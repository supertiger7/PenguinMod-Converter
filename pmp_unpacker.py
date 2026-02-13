"""
PenguinMod File Converter - Unpacker (FIXED)
Handles unpacking .pmp files to various folder structures
FIXES: 
- Preserves target order in metadata
- Properly handles customFonts
"""

import zipfile
import json
import shutil
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
import hashlib
import re

from pmp_logger import LogLevel
from pmp_types import ConverterType


class PMPUnpacker:
    """Handles unpacking .pmp files into folder structures"""
    
    def __init__(self):
        self.project_data = None
        self.temp_extract_dir = None
        
    def _cleanup_output_directory(self, output_dir: str, log_cb: Optional[Callable]):
        """Clean up existing output directory to avoid duplicate/orphaned files"""
        import shutil
        
        output_path = Path(output_dir)
        
        # If output directory doesn't exist, nothing to clean
        if not output_path.exists():
            if log_cb:
                log_cb(LogLevel.DEBUG, "CLEANUP", f"Output directory doesn't exist yet: {output_dir}")
            return
        
        if log_cb:
            log_cb(LogLevel.INFO, "CLEANUP", f"Cleaning existing output directory: {output_dir}")
        
        # Count files to be deleted
        files_to_delete = []
        dirs_to_delete = []
        
        for item in output_path.iterdir():
            # Skip the temp extraction directory
            if item.name == ".temp_extract":
                continue
                
            if item.is_file():
                files_to_delete.append(item)
            elif item.is_dir():
                dirs_to_delete.append(item)
        
        if not files_to_delete and not dirs_to_delete:
            if log_cb:
                log_cb(LogLevel.DEBUG, "CLEANUP", "Output directory is already empty")
            return
        
        # Log what will be deleted
        total_items = len(files_to_delete) + len(dirs_to_delete)
        if log_cb:
            log_cb(LogLevel.WARN, "CLEANUP", f"Deleting {total_items} items from output directory to avoid duplicates")
        
        # Delete files
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                if log_cb:
                    log_cb(LogLevel.DEBUG, "CLEANUP", f"Deleted file: {file_path.name}")
            except Exception as e:
                if log_cb:
                    log_cb(LogLevel.ERROR, "CLEANUP", f"Failed to delete file {file_path.name}: {e}")
        
        # Delete directories
        for dir_path in dirs_to_delete:
            try:
                shutil.rmtree(dir_path)
                if log_cb:
                    log_cb(LogLevel.DEBUG, "CLEANUP", f"Deleted directory: {dir_path.name}")
            except Exception as e:
                if log_cb:
                    log_cb(LogLevel.ERROR, "CLEANUP", f"Failed to delete directory {dir_path.name}: {e}")
        
        if log_cb:
            log_cb(LogLevel.INFO, "CLEANUP", f"✓ Cleanup complete - removed {len(files_to_delete)} files and {len(dirs_to_delete)} directories")
        
    def unpack(
        self,
        pmp_file: str,
        output_dir: str,
        converter_type: ConverterType,
        total_progress_cb: Optional[Callable] = None,
        item_progress_cb: Optional[Callable] = None,
        log_cb: Optional[Callable] = None
    ) -> bool:
        """Unpack .pmp file to folder structure"""
        try:
            # Step 1: Extract ZIP (10%)
            if total_progress_cb:
                total_progress_cb(0, "Extracting .pmp archive")
            if log_cb:
                log_cb(LogLevel.INFO, "UNPACKER", "Extracting .pmp archive")
                
            temp_dir = Path(output_dir) / ".temp_extract"
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.temp_extract_dir = temp_dir
            
            with zipfile.ZipFile(pmp_file, 'r') as zf:
                zf.extractall(temp_dir)
                
            if total_progress_cb:
                total_progress_cb(10, "Archive extracted")
                
            # Step 2: Load project.json (20%)
            if total_progress_cb:
                total_progress_cb(10, "Loading project.json")
            if log_cb:
                log_cb(LogLevel.INFO, "UNPACKER", "Loading project.json")
                
            project_json_path = temp_dir / "project.json"
            if not project_json_path.exists():
                if log_cb:
                    log_cb(LogLevel.FATAL, "UNPACKER", "project.json not found in archive")
                return False
                
            with open(project_json_path, 'r', encoding='utf-8') as f:
                self.project_data = json.load(f)
                
            if total_progress_cb:
                total_progress_cb(20, "Project data loaded")
                
            # Step 2.5: Clean up output directory if it exists
            if total_progress_cb:
                total_progress_cb(22, "Preparing output directory")
            self._cleanup_output_directory(output_dir, log_cb)
                
            # Step 3: Organize based on converter type (80%)
            if converter_type == ConverterType.LEGACY:
                success = self._unpack_legacy(output_dir, total_progress_cb, item_progress_cb, log_cb)
            elif converter_type == ConverterType.IDEA1:
                success = self._unpack_idea1(output_dir, total_progress_cb, item_progress_cb, log_cb)
            elif converter_type == ConverterType.IDEA2:
                success = self._unpack_idea2(output_dir, total_progress_cb, item_progress_cb, log_cb)
            elif converter_type == ConverterType.HIDDEN:
                success = self._unpack_hidden(output_dir, total_progress_cb, item_progress_cb, log_cb)
            else:
                if log_cb:
                    log_cb(LogLevel.FATAL, "UNPACKER", f"Unknown converter type: {converter_type}")
                return False
                
            # Step 4: Cleanup and metadata
            if success:
                if total_progress_cb:
                    total_progress_cb(95, "Writing metadata")
                    
                # Write metadata file for repacking
                # FIX: Include target order information
                targets = self.project_data.get('targets', [])
                target_order = []
                for target in targets:
                    is_stage = target.get('isStage', False)
                    target_name = target.get('name', 'unknown')
                    folder_name = "stage" if is_stage else self._sanitize_folder_name(target_name)
                    target_order.append({
                        'folder': folder_name,
                        'name': target_name,
                        'isStage': is_stage
                    })
                
                metadata = {
                    'converter_type': converter_type.value,
                    'original_file': Path(pmp_file).name,
                    'target_order': target_order  # FIX: Save original order
                }
                metadata_path = Path(output_dir) / ".pmp_metadata.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                    
                if log_cb:
                    log_cb(LogLevel.DEBUG, "UNPACKER", f"Saved metadata with {len(target_order)} targets in order")
                    
                if total_progress_cb:
                    total_progress_cb(100, "Complete")
                    
            # Cleanup temp directory
            if self.temp_extract_dir and self.temp_extract_dir.exists():
                shutil.rmtree(self.temp_extract_dir, ignore_errors=True)
                
            return success
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            if log_cb:
                log_cb(LogLevel.FATAL, "UNPACKER", f"Unpack failed: {str(e)}")
                log_cb(LogLevel.DEBUG, "UNPACKER", f"Traceback:\n{error_details}")
            return False
            
    def _sanitize_folder_name(self, name: str) -> str:
        """Convert sprite name to safe folder name"""
        # Replace // with _ to preserve folder structure info while being filesystem-safe
        safe_name = name.replace('//', '_')
        # Remove other unsafe characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '', safe_name)
        # Trim and remove trailing dots/spaces
        safe_name = safe_name.strip('. ')
        return safe_name if safe_name else 'sprite'
    
    def _sanitize_block_id(self, block_id: str) -> str:
        """Convert block ID to safe filename using URL encoding for special chars
        
        Windows doesn't allow these characters in filenames: < > : " / \\ | ? *
        We use URL encoding to preserve the exact block ID while making it filesystem-safe.
        
        IMPORTANT: The actual block IDs are preserved in the JSON files themselves.
        The sanitized version is ONLY used for filenames. When repacking, we read
        the block IDs from the JSON content, not from the filenames, so no
        reverse mapping is needed.
        
        Example:
            Block ID: "l*"  -> Filename: "child_l%2A.json"
            But the JSON contains: {"l*": {...}} with the original ID
        """
        safe_id = block_id
        # URL encode invalid Windows filename characters
        # CRITICAL: Must encode % first to avoid double-encoding!
        safe_id = safe_id.replace('%', '%25')  # percent sign (must be first!)
        safe_id = safe_id.replace('*', '%2A')  # asterisk
        safe_id = safe_id.replace('?', '%3F')  # question mark
        safe_id = safe_id.replace('<', '%3C')  # less than
        safe_id = safe_id.replace('>', '%3E')  # greater than
        safe_id = safe_id.replace(':', '%3A')  # colon
        safe_id = safe_id.replace('"', '%22')  # double quote
        safe_id = safe_id.replace('/', '%2F')  # forward slash
        safe_id = safe_id.replace('\\', '%5C') # backslash
        safe_id = safe_id.replace('|', '%7C')  # pipe
        return safe_id
        
    def _unpack_legacy(
        self,
        output_dir: str,
        total_progress_cb: Optional[Callable],
        item_progress_cb: Optional[Callable],
        log_cb: Optional[Callable]
    ) -> bool:
        """Unpack using legacy format (project.json + assets)"""
        if log_cb:
            log_cb(LogLevel.INFO, "UNPACKER", "Using LEGACY format")
            
        output_path = Path(output_dir)
        
        # Copy project.json
        if total_progress_cb:
            total_progress_cb(40, "Copying project.json")
            
        shutil.copy2(
            self.temp_extract_dir / "project.json",
            output_path / "project.json"
        )
        
        # Copy all asset files
        if total_progress_cb:
            total_progress_cb(50, "Copying assets")
            
        assets = [f for f in self.temp_extract_dir.iterdir() 
                 if f.is_file() and f.name != "project.json"]
                 
        if log_cb:
            log_cb(LogLevel.INFO, "UNPACKER", f"Copying {len(assets)} asset files")
            
        for idx, asset_file in enumerate(assets):
            if item_progress_cb:
                item_progress_cb(int((idx / max(len(assets), 1)) * 100), asset_file.name)
            
            dest = output_path / asset_file.name
            
            # Check if file already exists (shouldn't happen after cleanup)
            if dest.exists():
                if log_cb:
                    log_cb(LogLevel.WARN, "ASSET_MGR", f"Overwriting existing asset: {asset_file.name}")
            
            shutil.copy2(asset_file, dest)
            if log_cb:
                log_cb(LogLevel.DEBUG, "ASSET_MGR", f"Copied asset: {asset_file.name}")
                
        if total_progress_cb:
            total_progress_cb(90, "Legacy format complete")
            
        return True
        
    def _unpack_idea1(
        self,
        output_dir: str,
        total_progress_cb: Optional[Callable],
        item_progress_cb: Optional[Callable],
        log_cb: Optional[Callable]
    ) -> bool:
        """Unpack using Idea 1 format (sprites in folders)"""
        if log_cb:
            log_cb(LogLevel.INFO, "UNPACKER", "Using IDEA 1 (Refined) format")
            
        output_path = Path(output_dir)
        
        # Create main project.json with top-level data
        # FIX: Ensure customFonts are included in project.json
        if total_progress_cb:
            total_progress_cb(30, "Creating project structure")
            
        # Get customFonts with full data preservation
        custom_fonts = self.project_data.get('customFonts', [])
        
        project_meta = {
            'meta': self.project_data.get('meta', {}),
            'extensions': self.project_data.get('extensions', []),
            'extensionURLs': self.project_data.get('extensionURLs', {}),
            'extensionData': self.project_data.get('extensionData', {}),
            'monitors': self.project_data.get('monitors', []),
            'customFonts': custom_fonts  # FIX: Must be in main project.json with full data
        }
        
        # Preserve any unknown top-level keys
        for key in self.project_data:
            if key not in ['meta', 'extensions', 'extensionURLs', 'extensionData', 
                          'monitors', 'customFonts', 'targets']:
                project_meta[key] = self.project_data[key]
                if log_cb:
                    log_cb(LogLevel.DEBUG, "UNPACKER", f"Preserving unknown top-level key: {key}")
                    
        with open(output_path / "project.json", 'w', encoding='utf-8') as f:
            json.dump(project_meta, f, indent=2, ensure_ascii=False)
            
        if log_cb:
            font_details = f"Saved {len(custom_fonts)} custom fonts to project.json"
            if custom_fonts:
                font_names = [f.get('family', 'Unknown') for f in custom_fonts]
                font_details += f" ({', '.join(font_names)})"
            log_cb(LogLevel.DEBUG, "FONTS", font_details)
            
        # Handle extensions
        if total_progress_cb:
            total_progress_cb(35, "Processing extensions")
            
        extensions_dir = output_path / "extensions"
        extensions_dir.mkdir(exist_ok=True)
        
        # Create extensions index
        ext_index = {
            'extensions': self.project_data.get('extensions', []),
            'extensionURLs': self.project_data.get('extensionURLs', {})
        }
        with open(extensions_dir / "index.json", 'w', encoding='utf-8') as f:
            json.dump(ext_index, f, indent=2, ensure_ascii=False)
            
        # Extract font files to fonts folder
        if total_progress_cb:
            total_progress_cb(38, "Extracting fonts")
        self._extract_fonts(output_path, log_cb)
            
        # Process targets (sprites)
        targets = self.project_data.get('targets', [])
        if log_cb:
            log_cb(LogLevel.INFO, "UNPACKER", f"Processing {len(targets)} targets")
            
        sprites_dir = output_path / "sprites"
        sprites_dir.mkdir(exist_ok=True)
        
        # FIX: Process targets in order (order is preserved in metadata)
        for idx, target in enumerate(targets):
            progress = 40 + int((idx / len(targets)) * 50)
            if total_progress_cb:
                total_progress_cb(progress, f"Processing target {idx + 1}/{len(targets)}")
                
            target_name = target.get('name', f'target_{idx}')
            is_stage = target.get('isStage', False)
            
            # Use "stage" for stage, sanitize name for sprites
            folder_name = "stage" if is_stage else self._sanitize_folder_name(target_name)
            
            if log_cb:
                log_cb(LogLevel.INFO, "UNPACKER", f"Processing {'stage' if is_stage else 'sprite'}: {target_name}")
                
            target_dir = sprites_dir / folder_name
            target_dir.mkdir(exist_ok=True)
            
            # Process costumes
            self._process_costumes_idea1(target, target_dir, item_progress_cb, log_cb)
            
            # Process sounds
            self._process_sounds_idea1(target, target_dir, item_progress_cb, log_cb)
            
            # Create target JSON with all data except costumes/sounds assets
            target_json = {}
            for key in target:
                if key not in ['costumes', 'sounds']:
                    target_json[key] = target[key]
                elif key == 'costumes':
                    # Keep costume metadata but asset files are separate
                    target_json['costumes'] = [
                        {k: v for k, v in costume.items()} 
                        for costume in target.get('costumes', [])
                    ]
                elif key == 'sounds':
                    # Keep sound metadata but asset files are separate
                    target_json['sounds'] = [
                        {k: v for k, v in sound.items()} 
                        for sound in target.get('sounds', [])
                    ]
                    
            with open(target_dir / f"{folder_name}.json", 'w', encoding='utf-8') as f:
                json.dump(target_json, f, indent=2, ensure_ascii=False)
                
        if total_progress_cb:
            total_progress_cb(90, "Idea 1 format complete")
            
        return True
        
    def _process_costumes_idea1(self, target: Dict, target_dir: Path, 
                                 item_progress_cb: Optional[Callable],
                                 log_cb: Optional[Callable]):
        """Process costumes for Idea 1 format"""
        costumes = target.get('costumes', [])
        if not costumes:
            if log_cb:
                log_cb(LogLevel.NOTE, "ASSET_MGR", f"Sprite '{target.get('name', 'unknown')}' has no costumes; skipping folder")
            return
            
        costumes_dir = target_dir / "costumes"
        costumes_dir.mkdir(exist_ok=True)
        
        for costume in costumes:
            md5ext = costume.get('md5ext')
            if not md5ext:
                continue
                
            source = self.temp_extract_dir / md5ext
            if source.exists():
                dest = costumes_dir / md5ext
                
                # Check if file already exists (shouldn't happen after cleanup)
                if dest.exists():
                    if log_cb:
                        log_cb(LogLevel.WARN, "ASSET_MGR", f"Overwriting existing costume: {md5ext}")
                
                shutil.copy2(source, dest)
                if log_cb:
                    log_cb(LogLevel.DEBUG, "ASSET_MGR", f"Added costume: {md5ext}")
                    
    def _process_sounds_idea1(self, target: Dict, target_dir: Path,
                              item_progress_cb: Optional[Callable],
                              log_cb: Optional[Callable]):
        """Process sounds for Idea 1 format"""
        sounds = target.get('sounds', [])
        if not sounds:
            if log_cb:
                log_cb(LogLevel.NOTE, "ASSET_MGR", f"Sprite '{target.get('name', 'unknown')}' has no sound data; skipping folder.")
            return
            
        sounds_dir = target_dir / "sounds"
        sounds_dir.mkdir(exist_ok=True)
        
        for sound in sounds:
            md5ext = sound.get('md5ext')
            if not md5ext:
                continue
                
            source = self.temp_extract_dir / md5ext
            if source.exists():
                dest = sounds_dir / md5ext
                
                # Check if file already exists (shouldn't happen after cleanup)
                if dest.exists():
                    if log_cb:
                        log_cb(LogLevel.WARN, "ASSET_MGR", f"Overwriting existing sound: {md5ext}")
                
                shutil.copy2(source, dest)
                if log_cb:
                    log_cb(LogLevel.DEBUG, "ASSET_MGR", f"Added sound: {md5ext}")
                    
    def _extract_fonts(self, output_path: Path, log_cb: Optional[Callable]):
        """Extract font files from the archive to fonts folder"""
        custom_fonts = self.project_data.get('customFonts', [])
        
        if not custom_fonts:
            if log_cb:
                log_cb(LogLevel.DEBUG, "FONTS", "No custom fonts to extract")
            return
            
        fonts_dir = output_path / "fonts"
        fonts_dir.mkdir(exist_ok=True)
        
        extracted_count = 0
        for font in custom_fonts:
            md5ext = font.get('md5ext')
            if not md5ext:
                if log_cb:
                    log_cb(LogLevel.WARN, "FONTS", f"Font '{font.get('family', 'unknown')}' has no md5ext")
                continue
                
            source = self.temp_extract_dir / md5ext
            if source.exists():
                dest = fonts_dir / md5ext
                
                # Check if file already exists (shouldn't happen after cleanup)
                if dest.exists():
                    if log_cb:
                        log_cb(LogLevel.WARN, "FONTS", f"Overwriting existing font: {font.get('family', 'unknown')} ({md5ext})")
                
                shutil.copy2(source, dest)
                extracted_count += 1
                if log_cb:
                    log_cb(LogLevel.DEBUG, "FONTS", f"Extracted font: {font.get('family', 'unknown')} ({md5ext})")
            else:
                if log_cb:
                    log_cb(LogLevel.WARN, "FONTS", f"Font file not found: {md5ext} for font '{font.get('family', 'unknown')}'")
                    
        if log_cb and extracted_count > 0:
            log_cb(LogLevel.INFO, "FONTS", f"Extracted {extracted_count} font files to fonts folder")
                    
    def _unpack_idea2(self, output_dir: str, total_progress_cb: Optional[Callable],
                      item_progress_cb: Optional[Callable], log_cb: Optional[Callable]) -> bool:
        """Idea 2: Split by top-level blocks (precise collaboration)"""
        if log_cb:
            log_cb(LogLevel.INFO, "UNPACKER", "Using IDEA 2 (Precise) format")
            
        output_path = Path(output_dir)
        
        # Create main project.json (same as Idea 1)
        if total_progress_cb:
            total_progress_cb(30, "Creating project structure")
            
        project_meta = {
            'meta': self.project_data.get('meta', {}),
            'extensions': self.project_data.get('extensions', []),
            'extensionURLs': self.project_data.get('extensionURLs', {}),
            'extensionData': self.project_data.get('extensionData', {}),
            'monitors': self.project_data.get('monitors', []),
            'customFonts': self.project_data.get('customFonts', [])
        }
        
        # Preserve unknown top-level keys
        for key in self.project_data:
            if key not in ['meta', 'extensions', 'extensionURLs', 'extensionData', 
                          'monitors', 'customFonts', 'targets']:
                project_meta[key] = self.project_data[key]
                if log_cb:
                    log_cb(LogLevel.DEBUG, "UNPACKER", f"Preserving unknown top-level key: {key}")
                    
        with open(output_path / "project.json", 'w', encoding='utf-8') as f:
            json.dump(project_meta, f, indent=2, ensure_ascii=False)
            
        if log_cb:
            log_cb(LogLevel.DEBUG, "FONTS", f"Saved {len(project_meta.get('customFonts', []))} custom fonts to project.json")
            
        # Handle extensions
        if total_progress_cb:
            total_progress_cb(35, "Processing extensions")
            
        extensions_dir = output_path / "extensions"
        extensions_dir.mkdir(exist_ok=True)
        
        ext_index = {
            'extensions': self.project_data.get('extensions', []),
            'extensionURLs': self.project_data.get('extensionURLs', {})
        }
        with open(extensions_dir / "index.json", 'w', encoding='utf-8') as f:
            json.dump(ext_index, f, indent=2, ensure_ascii=False)
            
        # Extract font files to fonts folder
        if total_progress_cb:
            total_progress_cb(38, "Extracting fonts")
        self._extract_fonts(output_path, log_cb)
            
        # Process targets with block splitting
        targets = self.project_data.get('targets', [])
        if log_cb:
            log_cb(LogLevel.INFO, "UNPACKER", f"Processing {len(targets)} targets")
            
        sprites_dir = output_path / "sprites"
        sprites_dir.mkdir(exist_ok=True)
        
        for idx, target in enumerate(targets):
            progress = 40 + int((idx / len(targets)) * 50)
            if total_progress_cb:
                total_progress_cb(progress, f"Processing target {idx + 1}/{len(targets)}")
                
            target_name = target.get('name', f'target_{idx}')
            is_stage = target.get('isStage', False)
            folder_name = "stage" if is_stage else self._sanitize_folder_name(target_name)
            
            if log_cb:
                log_cb(LogLevel.INFO, "UNPACKER", f"Processing {'stage' if is_stage else 'sprite'}: {target_name}")
                
            target_dir = sprites_dir / folder_name
            target_dir.mkdir(exist_ok=True)
            
            # Process costumes and sounds (same as Idea 1)
            self._process_costumes_idea1(target, target_dir, item_progress_cb, log_cb)
            self._process_sounds_idea1(target, target_dir, item_progress_cb, log_cb)
            
            # Process blocks for Idea 2 (split by top-level stacks)
            self._process_blocks_idea2(target, target_dir, log_cb)
            
            # Create target JSON without blocks (they're in code/)
            target_json = {}
            for key in target:
                if key not in ['costumes', 'sounds', 'blocks']:
                    target_json[key] = target[key]
                elif key == 'costumes':
                    target_json['costumes'] = [
                        {k: v for k, v in costume.items()} 
                        for costume in target.get('costumes', [])
                    ]
                elif key == 'sounds':
                    target_json['sounds'] = [
                        {k: v for k, v in sound.items()} 
                        for sound in target.get('sounds', [])
                    ]
                    
            with open(target_dir / f"{folder_name}.json", 'w', encoding='utf-8') as f:
                json.dump(target_json, f, indent=2, ensure_ascii=False)
                
        if total_progress_cb:
            total_progress_cb(90, "Idea 2 format complete")
            
        return True
        
    def _process_blocks_idea2(self, target: Dict, target_dir: Path, log_cb: Optional[Callable]):
        """Split blocks by top-level stacks for Idea 2"""
        blocks = target.get('blocks', {})
        
        # Defensive check: blocks must be a dict (blockId -> blockObject)
        if not isinstance(blocks, dict):
            if log_cb:
                log_cb(LogLevel.ERROR, "UNPACKER", f"Target '{target.get('name', 'unknown')}' has invalid blocks structure (type: {type(blocks).__name__})")
            return
        
        if not blocks:
            if log_cb:
                log_cb(LogLevel.NOTE, "UNPACKER", f"Target '{target.get('name', 'unknown')}' has no blocks")
            return
            
        code_dir = target_dir / "code"
        code_dir.mkdir(exist_ok=True)
        
        # Track all blocks that will be written in stacks
        blocks_in_stacks = set()
        
        # Find all top-level blocks (only dict blocks can have topLevel property)
        top_level_blocks = []
        for block_id, block_data in blocks.items():
            # Only dict blocks can be top-level (need topLevel property)
            if not isinstance(block_data, dict):
                # Non-dict blocks will be preserved later
                if log_cb:
                    log_cb(LogLevel.DEBUG, "UNPACKER", f"Non-dict block {block_id} (type: {type(block_data).__name__}) - will preserve as detached")
                continue
            if block_data.get('topLevel', False):
                top_level_blocks.append(block_id)
                
        # Create index of top-level blocks
        index_data = {
            'topLevelBlocks': top_level_blocks,
            'totalBlocks': len(blocks)
        }
        with open(code_dir / "index.json", 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
            
        if log_cb:
            log_cb(LogLevel.DEBUG, "UNPACKER", f"Found {len(top_level_blocks)} top-level blocks in {len(blocks)} total blocks")
            
        # For each top-level block, collect it and all its children
        for top_block_id in top_level_blocks:
            stack_blocks = self._collect_block_stack(blocks, top_block_id)
            
            # Track which blocks are in this stack
            blocks_in_stacks.update(stack_blocks.keys())
            
            # Write this stack to a file
            # Use sanitized version of block ID for filename
            sanitized_id = self._sanitize_block_id(top_block_id)
            # Use first 2 chars for filename (after sanitization)
            short_id = sanitized_id[:2] if len(sanitized_id) >= 2 else sanitized_id
            block_file = code_dir / f"block-{short_id}.json"
            
            # If file exists, append a number
            counter = 1
            while block_file.exists():
                block_file = code_dir / f"block-{short_id}_{counter}.json"
                counter += 1
                
            with open(block_file, 'w', encoding='utf-8') as f:
                json.dump(stack_blocks, f, indent=2, ensure_ascii=False)
                
            if log_cb:
                log_cb(LogLevel.DEBUG, "UNPACKER", f"Wrote {len(stack_blocks)} blocks to {block_file.name}")
                
        # CRITICAL FIX: Preserve detached/orphan blocks (including non-dict ones)
        detached_blocks = {}
        for block_id, block_data in blocks.items():
            if block_id not in blocks_in_stacks:
                detached_blocks[block_id] = block_data
                
        if detached_blocks:
            detached_file = code_dir / "detached_blocks.json"
            with open(detached_file, 'w', encoding='utf-8') as f:
                json.dump(detached_blocks, f, indent=2, ensure_ascii=False)
            if log_cb:
                log_cb(LogLevel.DEBUG, "UNPACKER", f"Preserved {len(detached_blocks)} detached/non-dict blocks in {detached_file.name}")
                
                
    def _collect_block_stack(self, all_blocks: Dict, start_block_id: str) -> Dict:
        """Collect a top-level block and all its children recursively"""
        collected = {}
        to_process = [start_block_id]
        processed = set()
        
        while to_process:
            block_id = to_process.pop(0)
            if block_id in processed or block_id not in all_blocks:
                continue
                
            processed.add(block_id)
            block_data = all_blocks[block_id]
            
            # CRITICAL FIX: Preserve ALL blocks regardless of type (custom extensions)
            # Non-dict blocks are stored as-is (opaque preservation)
            if not isinstance(block_data, dict):
                # Preserve non-dict block opaquely
                collected[block_id] = block_data
                continue
                
            collected[block_id] = block_data
            
            # Add next block
            next_id = block_data.get('next')
            if next_id and isinstance(next_id, str):
                to_process.append(next_id)
                
            # Add inputs (recursively check for block references)
            inputs = block_data.get('inputs', {})
            if not isinstance(inputs, dict):
                continue
                
            for input_name, input_data in inputs.items():
                if isinstance(input_data, list) and len(input_data) >= 2:
                    # Input format is [type, value] or [type, value, ...]
                    # If value is a string, it might be a block ID
                    if isinstance(input_data[1], str) and input_data[1] in all_blocks:
                        to_process.append(input_data[1])
                        
            # Add substack inputs (for C-shaped blocks)
            if 'SUBSTACK' in inputs and isinstance(inputs['SUBSTACK'], list):
                if len(inputs['SUBSTACK']) >= 2 and isinstance(inputs['SUBSTACK'][1], str):
                    to_process.append(inputs['SUBSTACK'][1])
            if 'SUBSTACK2' in inputs and isinstance(inputs['SUBSTACK2'], list):
                if len(inputs['SUBSTACK2']) >= 2 and isinstance(inputs['SUBSTACK2'][1], str):
                    to_process.append(inputs['SUBSTACK2'][1])
                    
        return collected
        
    def _unpack_hidden(self, output_dir: str, total_progress_cb: Optional[Callable],
                       item_progress_cb: Optional[Callable], log_cb: Optional[Callable]) -> bool:
        """Hidden: Split by individual blocks (insane mode)"""
        if log_cb:
            log_cb(LogLevel.INFO, "UNPACKER", "Using HIDDEN (Insane) format")
            
        output_path = Path(output_dir)
        
        # Create main project.json (same as Idea 1)
        if total_progress_cb:
            total_progress_cb(30, "Creating project structure")
            
        project_meta = {
            'meta': self.project_data.get('meta', {}),
            'extensions': self.project_data.get('extensions', []),
            'extensionURLs': self.project_data.get('extensionURLs', {}),
            'extensionData': self.project_data.get('extensionData', {}),
            'monitors': self.project_data.get('monitors', []),
            'customFonts': self.project_data.get('customFonts', [])
        }
        
        # Preserve unknown top-level keys
        for key in self.project_data:
            if key not in ['meta', 'extensions', 'extensionURLs', 'extensionData', 
                          'monitors', 'customFonts', 'targets']:
                project_meta[key] = self.project_data[key]
                if log_cb:
                    log_cb(LogLevel.DEBUG, "UNPACKER", f"Preserving unknown top-level key: {key}")
                    
        with open(output_path / "project.json", 'w', encoding='utf-8') as f:
            json.dump(project_meta, f, indent=2, ensure_ascii=False)
            
        if log_cb:
            log_cb(LogLevel.DEBUG, "FONTS", f"Saved {len(project_meta.get('customFonts', []))} custom fonts to project.json")
            
        # Handle extensions
        if total_progress_cb:
            total_progress_cb(35, "Processing extensions")
            
        extensions_dir = output_path / "extensions"
        extensions_dir.mkdir(exist_ok=True)
        
        ext_index = {
            'extensions': self.project_data.get('extensions', []),
            'extensionURLs': self.project_data.get('extensionURLs', {})
        }
        with open(extensions_dir / "index.json", 'w', encoding='utf-8') as f:
            json.dump(ext_index, f, indent=2, ensure_ascii=False)
            
        # Extract font files to fonts folder
        if total_progress_cb:
            total_progress_cb(38, "Extracting fonts")
        self._extract_fonts(output_path, log_cb)
            
        # Process targets with individual block files
        targets = self.project_data.get('targets', [])
        if log_cb:
            log_cb(LogLevel.INFO, "UNPACKER", f"Processing {len(targets)} targets")
            
        sprites_dir = output_path / "sprites"
        sprites_dir.mkdir(exist_ok=True)
        
        for idx, target in enumerate(targets):
            progress = 40 + int((idx / len(targets)) * 50)
            if total_progress_cb:
                total_progress_cb(progress, f"Processing target {idx + 1}/{len(targets)}")
                
            target_name = target.get('name', f'target_{idx}')
            is_stage = target.get('isStage', False)
            folder_name = "stage" if is_stage else self._sanitize_folder_name(target_name)
            
            if log_cb:
                log_cb(LogLevel.INFO, "UNPACKER", f"Processing {'stage' if is_stage else 'sprite'}: {target_name}")
                
            target_dir = sprites_dir / folder_name
            target_dir.mkdir(exist_ok=True)
            
            # Process costumes and sounds (same as Idea 1)
            self._process_costumes_idea1(target, target_dir, item_progress_cb, log_cb)
            self._process_sounds_idea1(target, target_dir, item_progress_cb, log_cb)
            
            # Process blocks for Hidden (individual block files)
            self._process_blocks_hidden(target, target_dir, log_cb)
            
            # Create target JSON without blocks (they're in code/)
            target_json = {}
            for key in target:
                if key not in ['costumes', 'sounds', 'blocks']:
                    target_json[key] = target[key]
                elif key == 'costumes':
                    target_json['costumes'] = [
                        {k: v for k, v in costume.items()} 
                        for costume in target.get('costumes', [])
                    ]
                elif key == 'sounds':
                    target_json['sounds'] = [
                        {k: v for k, v in sound.items()} 
                        for sound in target.get('sounds', [])
                    ]
                    
            with open(target_dir / f"{folder_name}.json", 'w', encoding='utf-8') as f:
                json.dump(target_json, f, indent=2, ensure_ascii=False)
                
        if total_progress_cb:
            total_progress_cb(90, "Hidden format complete")
            
        return True
        
    def _process_blocks_hidden(self, target: Dict, target_dir: Path, log_cb: Optional[Callable]):
        """Split blocks into individual files (Hidden/Insane mode)"""
        blocks = target.get('blocks', {})
        
        # Defensive check: blocks must be a dict (blockId -> blockObject)
        if not isinstance(blocks, dict):
            if log_cb:
                log_cb(LogLevel.ERROR, "UNPACKER", f"Target '{target.get('name', 'unknown')}' has invalid blocks structure (type: {type(blocks).__name__})")
            return
        
        if not blocks:
            if log_cb:
                log_cb(LogLevel.NOTE, "UNPACKER", f"Target '{target.get('name', 'unknown')}' has no blocks")
            return
            
        code_dir = target_dir / "code"
        code_dir.mkdir(exist_ok=True)
        
        # Track all blocks that will be written in stacks
        blocks_in_stacks = set()
        
        # Find all top-level blocks (only dict blocks can have topLevel property)
        top_level_blocks = []
        for block_id, block_data in blocks.items():
            # Only dict blocks can be top-level (need topLevel property)
            if not isinstance(block_data, dict):
                # Non-dict blocks will be preserved later
                if log_cb:
                    log_cb(LogLevel.DEBUG, "UNPACKER", f"Non-dict block {block_id} (type: {type(block_data).__name__}) - will preserve as detached")
                continue
            if block_data.get('topLevel', False):
                top_level_blocks.append(block_id)
                
        # Create main index
        index_data = {
            'topLevelBlocks': top_level_blocks,
            'totalBlocks': len(blocks)
        }
        with open(code_dir / "index.json", 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
            
        if log_cb:
            log_cb(LogLevel.DEBUG, "UNPACKER", f"Found {len(top_level_blocks)} top-level blocks in {len(blocks)} total blocks")
            
        # For each top-level block, create a folder
        for top_block_id in top_level_blocks:
            # Collect the full stack
            stack_blocks = self._collect_block_stack(blocks, top_block_id)
            
            # Track which blocks are in this stack
            blocks_in_stacks.update(stack_blocks.keys())
            
            # Create folder for this parent using sanitized ID
            sanitized_id = self._sanitize_block_id(top_block_id)
            short_id = sanitized_id[:2] if len(sanitized_id) >= 2 else sanitized_id
            parent_dir = code_dir / f"parent_{short_id}"
            
            # Handle name collisions
            counter = 1
            while parent_dir.exists():
                parent_dir = code_dir / f"parent_{short_id}_{counter}"
                counter += 1
                
            parent_dir.mkdir(exist_ok=True)
            
            # Write parent block
            parent_data = {top_block_id: stack_blocks[top_block_id]}
            with open(parent_dir / f"parent_{short_id}.json", 'w', encoding='utf-8') as f:
                json.dump(parent_data, f, indent=2, ensure_ascii=False)
                
            # Write children blocks
            children_ids = [bid for bid in stack_blocks.keys() if bid != top_block_id]
            
            # Create index for children
            child_index = {
                'parentBlock': top_block_id,
                'children': children_ids
            }
            with open(parent_dir / "index.json", 'w', encoding='utf-8') as f:
                json.dump(child_index, f, indent=2, ensure_ascii=False)
                
            # Write each child block with sanitized filename
            for child_id in children_ids:
                sanitized_child_id = self._sanitize_block_id(child_id)
                child_short = sanitized_child_id[:2] if len(sanitized_child_id) >= 2 else sanitized_child_id
                child_file = parent_dir / f"child_{child_short}.json"
                
                # Handle collisions
                counter = 1
                while child_file.exists():
                    child_file = parent_dir / f"child_{child_short}_{counter}.json"
                    counter += 1
                    
                child_data = {child_id: stack_blocks[child_id]}
                with open(child_file, 'w', encoding='utf-8') as f:
                    json.dump(child_data, f, indent=2, ensure_ascii=False)
                    
            if log_cb:
                log_cb(LogLevel.DEBUG, "UNPACKER", f"Wrote parent with {len(children_ids)} children to {parent_dir.name}")
                
        # CRITICAL FIX: Preserve detached/orphan blocks (including non-dict ones)
        detached_blocks = {}
        for block_id, block_data in blocks.items():
            if block_id not in blocks_in_stacks:
                detached_blocks[block_id] = block_data
                
        if detached_blocks:
            detached_file = code_dir / "detached_blocks.json"
            with open(detached_file, 'w', encoding='utf-8') as f:
                json.dump(detached_blocks, f, indent=2, ensure_ascii=False)
            if log_cb:
                log_cb(LogLevel.DEBUG, "UNPACKER", f"Preserved {len(detached_blocks)} detached/non-dict blocks in {detached_file.name}")

