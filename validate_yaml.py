import yaml
import sys

def validate_yaml(file_path):
    try:
        with open(file_path, 'r') as file:
            yaml.safe_load(file)
        print(f"✅ YAML file {file_path} is valid")
        return True
    except yaml.YAMLError as e:
        print(f"❌ Error in {file_path}:")
        print(e)
        return False

if __name__ == "__main__":
    validate_yaml("config/config.yaml") 