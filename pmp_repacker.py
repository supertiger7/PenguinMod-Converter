"""
PenguinMod File Converter - Repacker (FIXED)
Handles repacking folder structures back to .pmp files
FIXES:
- Restores targets in original order from metadata
- Properly handles customFonts from project.json
- Preserves layerOrder exactly
"""

import zipfile
import json
import shutil
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

from pmp_logger import LogLevel
from pmp_types import ConverterType


class PMPRepacker:
    """Handles repacking folder structures back to .pmp files"""
    
    def __init__(self):
        self.project_data = None
        self.assets = []
        
    def repack(
        self,
        folder_path: str,
        output_file: str,
        converter_type: ConverterType,
        total_progress_cb: Optional[Callable] = None,
        item_progress_cb: Optional[Callable] = None,
        log_cb: Optional[Callable] = None
    ) -> bool:
        """Repack folder structure to .pmp file"""
        try:
            folder = Path(folder_path)
            
            # Step 1: Load and rebuild project data (70%)
            if total_progress_cb:
                total_progress_cb(0, "Loading project structure")
            if log_cb:
                log_cb(LogLevel.INFO, "REPACKER", "Loading project structure")
                
            if converter_type == ConverterType.LEGACY:
                success = self._repack_legacy(folder, total_progress_cb, item_progress_cb, log_cb)
            elif converter_type == ConverterType.IDEA1:
                success = self._repack_idea1(folder, total_progress_cb, item_progress_cb, log_cb)
            elif converter_type == ConverterType.IDEA2:
                success = self._repack_idea2(folder, total_progress_cb, item_progress_cb, log_cb)
            elif converter_type == ConverterType.HIDDEN:
                success = self._repack_hidden(folder, total_progress_cb, item_progress_cb, log_cb)
            else:
                if log_cb:
                    log_cb(LogLevel.FATAL, "REPACKER", f"Unknown converter type: {converter_type}")
                return False
                
            if not success:
                return False
                
            # Step 2: Create ZIP archive (90%)
            if total_progress_cb:
                total_progress_cb(75, "Creating .pmp archive")
            if log_cb:
                log_cb(LogLevel.INFO, "REPACKER", "Creating .pmp archive")
                
            # Create temp directory for staging
            temp_dir = Path(output_file).parent / ".temp_repack"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Write project.json
            project_json_path = temp_dir / "project.json"
            # FIX: Use separators without spaces for compact output
            with open(project_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, ensure_ascii=False, separators=(',', ':'))
                
            # Copy assets
            if total_progress_cb:
                total_progress_cb(80, "Copying assets")
                
            for asset_path in self.assets:
                if asset_path.exists():
                    dest = temp_dir / asset_path.name
                    shutil.copy2(asset_path, dest)
                    if log_cb:
                        log_cb(LogLevel.DEBUG, "REPACKER", f"Copied asset: {asset_path.name}")
                        
            # Create ZIP with optimized compression
            if total_progress_cb:
                total_progress_cb(85, "Compressing archive")
                
            # Use compression level 6 (balanced speed/size) instead of default 9
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for file_path in temp_dir.iterdir():
                    zf.write(file_path, file_path.name)
                    
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if total_progress_cb:
                total_progress_cb(100, "Complete")
            if log_cb:
                log_cb(LogLevel.INFO, "REPACKER", f"Created .pmp file: {output_file}")
                
            return True
            
        except Exception as e:
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", f"Repack failed: {str(e)}")
            return False
            
    def _repack_legacy(
        self,
        folder: Path,
        total_progress_cb: Optional[Callable],
        item_progress_cb: Optional[Callable],
        log_cb: Optional[Callable]
    ) -> bool:
        """Repack from legacy format"""
        if log_cb:
            log_cb(LogLevel.INFO, "REPACKER", "Using LEGACY format")
            
        # Load project.json
        project_json = folder / "project.json"
        if not project_json.exists():
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", "project.json not found")
            return False
            
        with open(project_json, 'r', encoding='utf-8') as f:
            self.project_data = json.load(f)
            
        # Collect all assets
        self.assets = [f for f in folder.iterdir() 
                      if f.is_file() and f.name != "project.json" and not f.name.startswith('.')]
                      
        if log_cb:
            log_cb(LogLevel.INFO, "REPACKER", f"Loaded project with {len(self.assets)} assets")
            
        if total_progress_cb:
            total_progress_cb(70, "Legacy format loaded")
            
        return True
        
    def _repack_idea1(
        self,
        folder: Path,
        total_progress_cb: Optional[Callable],
        item_progress_cb: Optional[Callable],
        log_cb: Optional[Callable]
    ) -> bool:
        """Repack from Idea 1 format"""
        if log_cb:
            log_cb(LogLevel.INFO, "REPACKER", "Using IDEA 1 (Refined) format")
            
        # Load main project.json
        project_json = folder / "project.json"
        if not project_json.exists():
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", "project.json not found")
            return False
            
        with open(project_json, 'r', encoding='utf-8') as f:
            self.project_data = json.load(f)
            
        # FIX: Load target order from metadata
        metadata_path = folder / ".pmp_metadata.json"
        target_order = []
        
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                target_order = metadata.get('target_order', [])
                if log_cb:
                    log_cb(LogLevel.INFO, "REPACKER", f"Loaded target order from metadata: {len(target_order)} targets")
        else:
            if log_cb:
                log_cb(LogLevel.WARN, "REPACKER", "No metadata found - will attempt to preserve order from filesystem")
                
        # Load targets from sprites directory
        sprites_dir = folder / "sprites"
        if not sprites_dir.exists():
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", "sprites directory not found")
            return False
            
        targets = []
        self.assets = []
        
        # FIX: Use target_order from metadata if available
        if target_order:
            # Process targets in the exact order from metadata
            for idx, target_info in enumerate(target_order):
                folder_name = target_info['folder']
                target_dir = sprites_dir / folder_name
                
                if not target_dir.exists():
                    if log_cb:
                        log_cb(LogLevel.ERROR, "REPACKER", f"Target folder not found: {folder_name}")
                    continue
                    
                progress = 20 + int((idx / max(len(target_order), 1)) * 50)
                if total_progress_cb:
                    total_progress_cb(progress, f"Loading target {idx + 1}/{len(target_order)}")
                    
                target, sprite_assets = self._load_target_idea1(target_dir, folder_name, log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(sprite_assets)
                    if log_cb:
                        log_cb(LogLevel.DEBUG, "REPACKER", f"Loaded target in order: {target.get('name', folder_name)}")
        else:
            # Fallback: Process stage first, then other sprites alphabetically
            # This is not ideal but better than random order
            if log_cb:
                log_cb(LogLevel.WARN, "REPACKER", "Using fallback alphabetical order - results may not match original")
                
            stage_dir = sprites_dir / "stage"
            if stage_dir.exists():
                if total_progress_cb:
                    total_progress_cb(20, "Loading stage")
                target, stage_assets = self._load_target_idea1(stage_dir, "stage", log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(stage_assets)
                    
            # FIX: Sort sprite directories alphabetically for deterministic order
            sprite_dirs = sorted([d for d in sprites_dir.iterdir() 
                                 if d.is_dir() and d.name != "stage"],
                                key=lambda x: x.name)
            
            if log_cb:
                log_cb(LogLevel.INFO, "REPACKER", f"Found {len(sprite_dirs)} sprite folders")
                
            for idx, sprite_dir in enumerate(sprite_dirs):
                progress = 20 + int((idx / max(len(sprite_dirs), 1)) * 50)
                if total_progress_cb:
                    total_progress_cb(progress, f"Loading sprite {idx + 1}/{len(sprite_dirs)}")
                    
                target, sprite_assets = self._load_target_idea1(sprite_dir, sprite_dir.name, log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(sprite_assets)
                    
        self.project_data['targets'] = targets
        
        # Load font files from fonts folder
        self._load_fonts(folder, log_cb)
        
        if log_cb:
            log_cb(LogLevel.INFO, "REPACKER", f"Loaded {len(targets)} targets with {len(self.assets)} assets")
            
        if total_progress_cb:
            total_progress_cb(70, "Idea 1 format loaded")
            
        return True
        
    def _load_target_idea1(self, target_dir: Path, folder_name: str, 
                           log_cb: Optional[Callable]) -> tuple:
        """Load a target from Idea 1 format"""
        target_json_path = target_dir / f"{folder_name}.json"
        
        if not target_json_path.exists():
            if log_cb:
                log_cb(LogLevel.ERROR, "REPACKER", f"Target JSON not found: {target_json_path}")
            return None, []
            
        with open(target_json_path, 'r', encoding='utf-8') as f:
            target = json.load(f)
            
        # Collect assets from costumes and sounds folders
        assets = []
        
        costumes_dir = target_dir / "costumes"
        if costumes_dir.exists():
            for asset_file in costumes_dir.iterdir():
                if asset_file.is_file():
                    assets.append(asset_file)
                    
        sounds_dir = target_dir / "sounds"
        if sounds_dir.exists():
            for asset_file in sounds_dir.iterdir():
                if asset_file.is_file():
                    assets.append(asset_file)
                    
        return target, assets
        
    def _repack_idea2(
        self,
        folder: Path,
        total_progress_cb: Optional[Callable],
        item_progress_cb: Optional[Callable],
        log_cb: Optional[Callable]
    ) -> bool:
        """Repack from Idea 2 format (split by top-level blocks)"""
        if log_cb:
            log_cb(LogLevel.INFO, "REPACKER", "Using IDEA 2 (Precise) format")
            
        # Load main project.json
        project_json = folder / "project.json"
        if not project_json.exists():
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", "project.json not found")
            return False
            
        with open(project_json, 'r', encoding='utf-8') as f:
            self.project_data = json.load(f)
            
        # Load target order from metadata
        metadata_path = folder / ".pmp_metadata.json"
        target_order = []
        
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                target_order = metadata.get('target_order', [])
                if log_cb:
                    log_cb(LogLevel.INFO, "REPACKER", f"Loaded target order from metadata: {len(target_order)} targets")
        else:
            if log_cb:
                log_cb(LogLevel.WARN, "REPACKER", "No metadata found - will attempt to preserve order from filesystem")
                
        # Load targets from sprites directory
        sprites_dir = folder / "sprites"
        if not sprites_dir.exists():
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", "sprites directory not found")
            return False
            
        targets = []
        self.assets = []
        
        # Use target_order from metadata if available
        if target_order:
            for idx, target_info in enumerate(target_order):
                folder_name = target_info['folder']
                target_dir = sprites_dir / folder_name
                
                if not target_dir.exists():
                    if log_cb:
                        log_cb(LogLevel.ERROR, "REPACKER", f"Target folder not found: {folder_name}")
                    continue
                    
                progress = 20 + int((idx / max(len(target_order), 1)) * 50)
                if total_progress_cb:
                    total_progress_cb(progress, f"Loading target {idx + 1}/{len(target_order)}")
                    
                target, sprite_assets = self._load_target_idea2(target_dir, folder_name, log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(sprite_assets)
                    if log_cb:
                        log_cb(LogLevel.DEBUG, "REPACKER", f"Loaded target in order: {target.get('name', folder_name)}")
        else:
            # Fallback: stage first, then alphabetically
            if log_cb:
                log_cb(LogLevel.WARN, "REPACKER", "Using fallback alphabetical order")
                
            stage_dir = sprites_dir / "stage"
            if stage_dir.exists():
                if total_progress_cb:
                    total_progress_cb(20, "Loading stage")
                target, stage_assets = self._load_target_idea2(stage_dir, "stage", log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(stage_assets)
                    
            sprite_dirs = sorted([d for d in sprites_dir.iterdir() 
                                 if d.is_dir() and d.name != "stage"],
                                key=lambda x: x.name)
            
            for idx, sprite_dir in enumerate(sprite_dirs):
                progress = 20 + int((idx / max(len(sprite_dirs), 1)) * 50)
                if total_progress_cb:
                    total_progress_cb(progress, f"Loading sprite {idx + 1}/{len(sprite_dirs)}")
                    
                target, sprite_assets = self._load_target_idea2(sprite_dir, sprite_dir.name, log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(sprite_assets)
                    
        self.project_data['targets'] = targets
        
        # Load font files from fonts folder
        self._load_fonts(folder, log_cb)
        
        if log_cb:
            log_cb(LogLevel.INFO, "REPACKER", f"Loaded {len(targets)} targets with {len(self.assets)} assets")
            
        if total_progress_cb:
            total_progress_cb(70, "Idea 2 format loaded")
            
        return True
        
    def _load_target_idea2(self, target_dir: Path, folder_name: str, 
                           log_cb: Optional[Callable]) -> tuple:
        """Load a target from Idea 2 format (with split blocks)"""
        target_json_path = target_dir / f"{folder_name}.json"
        
        if not target_json_path.exists():
            if log_cb:
                log_cb(LogLevel.ERROR, "REPACKER", f"Target JSON not found: {target_json_path}")
            return None, []
            
        with open(target_json_path, 'r', encoding='utf-8') as f:
            target = json.load(f)
            
        # Load blocks from code directory
        code_dir = target_dir / "code"
        if code_dir.exists():
            all_blocks = {}
            
            # Read all block files
            for block_file in code_dir.iterdir():
                if block_file.is_file() and block_file.name.startswith('block-') and block_file.name.endswith('.json'):
                    with open(block_file, 'r', encoding='utf-8') as f:
                        blocks_data = json.load(f)
                        all_blocks.update(blocks_data)
                        
            # CRITICAL FIX: Load detached blocks (including non-dict custom extension blocks)
            detached_file = code_dir / "detached_blocks.json"
            if detached_file.exists():
                with open(detached_file, 'r', encoding='utf-8') as f:
                    detached_data = json.load(f)
                    all_blocks.update(detached_data)
                if log_cb:
                    log_cb(LogLevel.DEBUG, "REPACKER", f"Restored {len(detached_data)} detached/non-dict blocks")
                        
            target['blocks'] = all_blocks
            
            if log_cb:
                log_cb(LogLevel.DEBUG, "REPACKER", f"Loaded {len(all_blocks)} blocks for {folder_name}")
        else:
            target['blocks'] = {}
            
        # Collect assets
        assets = []
        
        costumes_dir = target_dir / "costumes"
        if costumes_dir.exists():
            for asset_file in costumes_dir.iterdir():
                if asset_file.is_file():
                    assets.append(asset_file)
                    
        sounds_dir = target_dir / "sounds"
        if sounds_dir.exists():
            for asset_file in sounds_dir.iterdir():
                if asset_file.is_file():
                    assets.append(asset_file)
                    
        return target, assets
        
    def _repack_hidden(
        self,
        folder: Path,
        total_progress_cb: Optional[Callable],
        item_progress_cb: Optional[Callable],
        log_cb: Optional[Callable]
    ) -> bool:
        """Repack from Hidden format (individual block files)"""
        if log_cb:
            log_cb(LogLevel.INFO, "REPACKER", "Using HIDDEN (Insane) format")
            
        # Load main project.json
        project_json = folder / "project.json"
        if not project_json.exists():
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", "project.json not found")
            return False
            
        with open(project_json, 'r', encoding='utf-8') as f:
            self.project_data = json.load(f)
            
        # Load target order from metadata
        metadata_path = folder / ".pmp_metadata.json"
        target_order = []
        
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                target_order = metadata.get('target_order', [])
                if log_cb:
                    log_cb(LogLevel.INFO, "REPACKER", f"Loaded target order from metadata: {len(target_order)} targets")
        else:
            if log_cb:
                log_cb(LogLevel.WARN, "REPACKER", "No metadata found")
                
        # Load targets from sprites directory
        sprites_dir = folder / "sprites"
        if not sprites_dir.exists():
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", "sprites directory not found")
            return False
            
        targets = []
        self.assets = []
        
        # Use target_order from metadata if available
        if target_order:
            for idx, target_info in enumerate(target_order):
                folder_name = target_info['folder']
                target_dir = sprites_dir / folder_name
                
                if not target_dir.exists():
                    if log_cb:
                        log_cb(LogLevel.ERROR, "REPACKER", f"Target folder not found: {folder_name}")
                    continue
                    
                progress = 20 + int((idx / max(len(target_order), 1)) * 50)
                if total_progress_cb:
                    total_progress_cb(progress, f"Loading target {idx + 1}/{len(target_order)}")
                    
                target, sprite_assets = self._load_target_hidden(target_dir, folder_name, log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(sprite_assets)
                    if log_cb:
                        log_cb(LogLevel.DEBUG, "REPACKER", f"Loaded target in order: {target.get('name', folder_name)}")
        else:
            # Fallback
            if log_cb:
                log_cb(LogLevel.WARN, "REPACKER", "Using fallback alphabetical order")
                
            stage_dir = sprites_dir / "stage"
            if stage_dir.exists():
                if total_progress_cb:
                    total_progress_cb(20, "Loading stage")
                target, stage_assets = self._load_target_hidden(stage_dir, "stage", log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(stage_assets)
                    
            sprite_dirs = sorted([d for d in sprites_dir.iterdir() 
                                 if d.is_dir() and d.name != "stage"],
                                key=lambda x: x.name)
            
            for idx, sprite_dir in enumerate(sprite_dirs):
                progress = 20 + int((idx / max(len(sprite_dirs), 1)) * 50)
                if total_progress_cb:
                    total_progress_cb(progress, f"Loading sprite {idx + 1}/{len(sprite_dirs)}")
                    
                target, sprite_assets = self._load_target_hidden(sprite_dir, sprite_dir.name, log_cb)
                if target:
                    targets.append(target)
                    self.assets.extend(sprite_assets)
                    
        self.project_data['targets'] = targets
        
        # Load font files from fonts folder
        self._load_fonts(folder, log_cb)
        
        if log_cb:
            log_cb(LogLevel.INFO, "REPACKER", f"Loaded {len(targets)} targets with {len(self.assets)} assets")
            
        if total_progress_cb:
            total_progress_cb(70, "Hidden format loaded")
            
        return True
        
    def _load_target_hidden(self, target_dir: Path, folder_name: str, 
                            log_cb: Optional[Callable]) -> tuple:
        """Load a target from Hidden format (individual block files)"""
        target_json_path = target_dir / f"{folder_name}.json"
        
        if not target_json_path.exists():
            if log_cb:
                log_cb(LogLevel.ERROR, "REPACKER", f"Target JSON not found: {target_json_path}")
            return None, []
            
        with open(target_json_path, 'r', encoding='utf-8') as f:
            target = json.load(f)
            
        # Load blocks from code directory
        code_dir = target_dir / "code"
        if code_dir.exists():
            all_blocks = {}
            
            # Read all parent folders
            for parent_dir in code_dir.iterdir():
                if parent_dir.is_dir() and parent_dir.name.startswith('parent_'):
                    # Read parent block
                    for block_file in parent_dir.iterdir():
                        if block_file.name.startswith('parent_') and block_file.name.endswith('.json'):
                            with open(block_file, 'r', encoding='utf-8') as f:
                                parent_data = json.load(f)
                                all_blocks.update(parent_data)
                                
                        # Read child blocks
                        elif block_file.name.startswith('child_') and block_file.name.endswith('.json'):
                            with open(block_file, 'r', encoding='utf-8') as f:
                                child_data = json.load(f)
                                all_blocks.update(child_data)
                        
            # CRITICAL FIX: Load detached blocks (including non-dict custom extension blocks)
            detached_file = code_dir / "detached_blocks.json"
            if detached_file.exists():
                with open(detached_file, 'r', encoding='utf-8') as f:
                    detached_data = json.load(f)
                    all_blocks.update(detached_data)
                if log_cb:
                    log_cb(LogLevel.DEBUG, "REPACKER", f"Restored {len(detached_data)} detached/non-dict blocks")
                        
            target['blocks'] = all_blocks
            
            if log_cb:
                log_cb(LogLevel.DEBUG, "REPACKER", f"Loaded {len(all_blocks)} blocks for {folder_name}")
        else:
            target['blocks'] = {}
            
        # Collect assets
        assets = []
        
        costumes_dir = target_dir / "costumes"
        if costumes_dir.exists():
            for asset_file in costumes_dir.iterdir():
                if asset_file.is_file():
                    assets.append(asset_file)
                    
        sounds_dir = target_dir / "sounds"
        if sounds_dir.exists():
            for asset_file in sounds_dir.iterdir():
                if asset_file.is_file():
                    assets.append(asset_file)
                    
        return target, assets
        
    def _load_fonts(self, folder: Path, log_cb: Optional[Callable]):
        """Load font files from fonts folder and add to assets"""
        fonts_dir = folder / "fonts"
        
        if not fonts_dir.exists():
            if log_cb:
                log_cb(LogLevel.DEBUG, "FONTS", "No fonts folder found")
            return
            
        font_count = 0
        for font_file in fonts_dir.iterdir():
            if font_file.is_file() and font_file.suffix in ['.ttf', '.otf', '.woff', '.woff2']:
                self.assets.append(font_file)
                font_count += 1
                if log_cb:
                    log_cb(LogLevel.DEBUG, "FONTS", f"Loaded font file: {font_file.name}")
                    
        if log_cb and font_count > 0:
            log_cb(LogLevel.INFO, "FONTS", f"Loaded {font_count} font files from fonts folder")
