import yaml
from yaml.loader import SafeLoader
import json
import streamlit_authenticator as stauth

with open('authentication_settings.yaml') as file:
     credentials = yaml.load(file, Loader=SafeLoader)
print(credentials)
# with open('credentials.json','w') as file:
#      credentials_json = json.dump(credentials,file,indent=4)

# with open('credentials.json','r') as file:
#      json.load(file)