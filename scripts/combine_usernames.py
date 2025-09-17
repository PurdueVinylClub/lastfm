def combine_usernames():
    # assume equal weighting

    usernames = []
    with open('usernames/dues_payers.txt', 'r') as f:
        usernames.extend(f.read().splitlines())

    with open('usernames/officers.txt', 'r') as f:
        usernames.extend(f.read().splitlines())

    with open('usernames_special.txt', 'w') as f: # write just officers/dues payers
        f.write("\n".join(usernames))

    with open('usernames/members.txt', 'r') as f:
        usernames = f.read().splitlines()

    with open('usernames.txt', 'w') as f: # write all members
        f.write("\n".join(usernames))

if __name__ == "__main__":
    combine_usernames()