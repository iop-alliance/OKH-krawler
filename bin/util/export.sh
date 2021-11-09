find . -name *.ttl -printf "%h\n" -exec cp --parents -t ../export {} \;
find . -name *.toml -printf "%h\n" -exec cp --parents -t ../export {} \;