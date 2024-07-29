import json
import os
from werkzeug.utils import secure_filename

SOUND_FILES_JSON = 'sound_files.json'

def convert_sound_files_structure():
    if os.path.exists(SOUND_FILES_JSON):
        with open(SOUND_FILES_JSON, 'r') as f:
            data = json.load(f)

        if "sounds" in data and isinstance(data["sounds"], list):
            transformed_sounds = []
            for sound in data["sounds"]:
                if isinstance(sound, str):
                    transformed_sounds.append({
                        "name": sound,
                        "filename": secure_filename(sound)
                    })

            with open(SOUND_FILES_JSON, 'w') as f:
                json.dump({"sounds": transformed_sounds}, f, indent=4)

convert_sound_files_structure()
print("Sound files structure converted successfully.")