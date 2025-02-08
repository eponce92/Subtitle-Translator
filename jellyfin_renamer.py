import os
import shutil
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class JellyfinRenamer:
    def __init__(self):
        self.LANGUAGE_CODES = {
            'english': 'en',  # Using ISO 639-1 codes for Jellyfin
            'spanish': 'es',
            'french': 'fr',
            'german': 'de',
            'italian': 'it',
            'portuguese': 'pt',
            'russian': 'ru',
            'japanese': 'ja',
            'korean': 'ko',
            'chinese': 'zh'
        }

    def _get_base_filename(self, filename):
        """Extract the base filename without stream numbers and language codes"""
        # Remove common patterns that we don't want in the final name
        patterns_to_remove = [
            r'_stream_\d+',  # Remove stream numbers
            r'_Spanish',     # Remove language suffix
            r'\.eng$',       # Remove .eng extension
            r'\.spa$'        # Remove .spa extension
        ]
        
        base = filename
        for pattern in patterns_to_remove:
            base = re.sub(pattern, '', base)
            
        return base.rsplit('.', 1)[0]  # Remove the extension

    def _generate_jellyfin_name(self, filename, flags=None):
        """Generate Jellyfin-compliant subtitle filename"""
        # Get the base filename without stream numbers and language codes
        video_name = self._get_base_filename(filename)
        
        # Build new name parts
        new_parts = [video_name]
        
        # Add language code
        if 'Spanish' in filename or '.spa.' in filename:
            new_parts.append('es')
        elif '.eng.' in filename:
            new_parts.append('en')
            
        # Add flags in Jellyfin order
        if flags:
            if flags.get('default'):
                new_parts.append('default')
            if flags.get('forced'):
                new_parts.append('forced')
            if flags.get('sdh'):
                new_parts.append('sdh')
                
        # Add extension
        new_parts.append('srt')
        
        # Join with dots
        return '.'.join(new_parts)

    def rename_subtitles(self, folder_path, flags=None, cleanup_originals=True):
        """
        Rename subtitle files to Jellyfin standard naming
        flags: dict of flags to add (e.g., {'forced': True, 'default': True, 'sdh': False})
        cleanup_originals: if True, delete original subtitle files after successful rename
        """
        renamed = []
        errors = []
        deleted = []
        
        try:
            # Walk through the folder
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.endswith('.srt'):
                        try:
                            old_path = os.path.join(root, file)
                            new_name = self._generate_jellyfin_name(file, flags)
                            new_path = os.path.join(root, new_name)
                            
                            # Skip if the file would be renamed to itself
                            if old_path.lower() == new_path.lower():
                                continue
                                
                            # Rename file
                            if os.path.exists(new_path):
                                logger.warning(f"Target file already exists, creating backup: {new_path}")
                                backup_path = new_path + '.bak'
                                shutil.move(new_path, backup_path)
                            
                            # Copy to new name first, then delete original if successful
                            shutil.copy2(old_path, new_path)
                            renamed.append((old_path, new_path))
                            logger.info(f"Renamed: {file} -> {new_name}")
                            
                            # Delete original if cleanup is enabled
                            if cleanup_originals:
                                os.remove(old_path)
                                deleted.append(old_path)
                                logger.info(f"Deleted original file: {file}")
                                
                        except Exception as e:
                            errors.append((file, str(e)))
                            logger.error(f"Error processing {file}: {e}")
                            
        except Exception as e:
            logger.error(f"Error processing folder {folder_path}: {e}")
            errors.append(("folder_processing", str(e)))
            
        return renamed, deleted, errors

    def preview_changes(self, folder_path, flags=None):
        """Preview what changes would be made without actually copying"""
        changes = []
        try:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.endswith('.srt'):
                        old_name = file
                        new_name = self._generate_jellyfin_name(file, flags)
                        if old_name.lower() != new_name.lower():  # Case-insensitive comparison
                            changes.append((old_name, new_name))
        except Exception as e:
            logger.error(f"Error previewing changes: {e}")
            
        return changes