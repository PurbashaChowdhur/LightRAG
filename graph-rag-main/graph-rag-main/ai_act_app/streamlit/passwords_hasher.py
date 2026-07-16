import streamlit_authenticator as stauth
import yaml
from yaml import SafeLoader

passwords_in_chiaro = ["Passw0rd!","def"]

hashed_passwords = stauth.Hasher().hash_list(passwords_in_chiaro)

print("Ecco le password hashate:")
for p in hashed_passwords:
    print(p)
