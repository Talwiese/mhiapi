import os
import yaml
import logging.config
import logging

def setup_logging(default_level=logging.INFO):
    """

    """
    config_path = "./config.yaml" if os.path.isfile("./config.yaml") else "./config_default.yaml"
    with open(config_path, 'rt') as f:
        try:
            cfg = yaml.safe_load(f.read()).get('logging')
            logging.config.dictConfig(cfg)
        except Exception as e:
            print(e)
            print('Error in Logging Configuration. Using default configs')
            logging.basicConfig(level=default_level)
    
    print(cfg)
