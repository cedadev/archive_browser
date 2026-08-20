import re
s = "/hel>/me_y/lo-1.23"
pattern = r"[a-zA-Z0-9/.\-_]+"

s = ""

if re.fullmatch(pattern, s):
    print("Valid string")
else:
    print("Invalid string")


