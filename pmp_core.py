"""
PenguinMod File Converter - Core Converter
Main converter logic coordinating unpack/repack operations
"""

from pathlib import Path
from typing import Callable, Optional
import zipfile
import json

from pmp_logger import LogLevel
from pmp_types import ConverterType
from pmp_unpacker import PMPUnpacker
from pmp_repacker import PMPRepacker


class PMPConverter:
    """Main converter orchestrating unpack and repack operations"""
    
    def __init__(self):
        self.unpacker = PMPUnpacker()
        self.repacker = PMPRepacker()
        
    def unpack(
        self,
        pmp_file: str,
        output_dir: str,
        converter_type: ConverterType,
        total_progress_cb: Optional[Callable] = None,
        item_progress_cb: Optional[Callable] = None,
        log_cb: Optional[Callable] = None
    ) -> bool:
        """
        Unpack a .pmp file to a folder structure
        
        Args:
            pmp_file: Path to .pmp file
            output_dir: Output directory
            converter_type: Type of converter to use
            total_progress_cb: Callback for total progress (percent, message)
            item_progress_cb: Callback for item progress (percent, message)
            log_cb: Callback for log messages (level, source, message)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if log_cb:
                log_cb(LogLevel.INFO, "UNPACKER", f"Starting unpack with {converter_type.name} format")
                log_cb(LogLevel.INFO, "UNPACKER", f"Input: {pmp_file}")
                log_cb(LogLevel.INFO, "UNPACKER", f"Output: {output_dir}")
                
            # Validate input
            if not Path(pmp_file).exists():
                if log_cb:
                    log_cb(LogLevel.FATAL, "UNPACKER", f"Input file does not exist: {pmp_file}")
                return False
                
            if not zipfile.is_zipfile(pmp_file):
                if log_cb:
                    log_cb(LogLevel.FATAL, "UNPACKER", "Input file is not a valid .pmp/.zip file")
                return False
                
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Perform unpacking
            success = self.unpacker.unpack(
                pmp_file,
                output_dir,
                converter_type,
                total_progress_cb,
                item_progress_cb,
                log_cb
            )
            
            if success and log_cb:
                log_cb(LogLevel.INFO, "UNPACKER", "Unpack completed successfully")
                
            return success
            
        except Exception as e:
            if log_cb:
                log_cb(LogLevel.FATAL, "UNPACKER", f"Unpack failed with exception: {str(e)}")
            return False
            
    def repack(
        self,
        folder_path: str,
        output_file: str,
        converter_type: ConverterType,
        total_progress_cb: Optional[Callable] = None,
        item_progress_cb: Optional[Callable] = None,
        log_cb: Optional[Callable] = None
    ) -> bool:
        """
        Repack a folder structure to a .pmp file
        
        Args:
            folder_path: Path to unpacked folder
            output_file: Output .pmp file path
            converter_type: Type of converter used during unpacking
            total_progress_cb: Callback for total progress (percent, message)
            item_progress_cb: Callback for item progress (percent, message)
            log_cb: Callback for log messages (level, source, message)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if log_cb:
                log_cb(LogLevel.INFO, "REPACKER", f"Starting repack with {converter_type.name} format")
                log_cb(LogLevel.INFO, "REPACKER", f"Input: {folder_path}")
                log_cb(LogLevel.INFO, "REPACKER", f"Output: {output_file}")
                
            # Validate input
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                if log_cb:
                    log_cb(LogLevel.FATAL, "REPACKER", f"Input folder does not exist: {folder_path}")
                return False
                
            # Detect converter type if metadata exists
            metadata_file = folder / ".pmp_metadata.json"
            detected_type = None
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        detected_type_str = metadata.get('converter_type')
                        if detected_type_str:
                            detected_type = ConverterType(detected_type_str)
                            if log_cb:
                                log_cb(LogLevel.INFO, "REPACKER", f"Detected converter type from metadata: {detected_type.name}")
                except Exception as e:
                    if log_cb:
                        log_cb(LogLevel.WARN, "REPACKER", f"Could not read metadata: {str(e)}")
                        
            # Use detected type if available and different from selected
            if detected_type and detected_type != converter_type:
                if log_cb:
                    log_cb(LogLevel.WARN, "REPACKER", f"Selected type ({converter_type.name}) differs from detected type ({detected_type.name})")
                    log_cb(LogLevel.INFO, "REPACKER", f"Using detected type: {detected_type.name}")
                converter_type = detected_type
                
            # Perform repacking
            success = self.repacker.repack(
                folder_path,
                output_file,
                converter_type,
                total_progress_cb,
                item_progress_cb,
                log_cb
            )
            
            if success and log_cb:
                log_cb(LogLevel.INFO, "REPACKER", "Repack completed successfully")
                
            return success
            
        except Exception as e:
            if log_cb:
                log_cb(LogLevel.FATAL, "REPACKER", f"Repack failed with exception: {str(e)}")
            return False
