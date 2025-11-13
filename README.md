# Learning Platform Project

## Installs Needed

### Learning Platform Request Collection

1. Install your favorite API testing tool. (E.g. Postman, Insomnia, Yaak)

## Getting Started

1. Clone this repo.
1. `cd` into the project directory.

## Github OAuth App

1. Go to your Github account settings
2. Open **Developer Settings**
3. Open **OAuth Apps**
4. Click **New OAuth App** button
5. Application name should be **Learning Platform**
6. Homepage URL should be `http://localhost:3000`
7. Enter a description if you like
8. Authorization callback should be `http://localhost:8000/auth/github/callback`
9. Leave **Enable Device Flow** unchecked
10. Create the app and **do not close** the screen that appears
11. Go to Github and click the **Generate a new client secret** button
12. **DO NOT CLOSE TAB. CLIENT AND SECRET NEEDED BELOW.**

### Django Secret Key

You will need a Django secret key environment variable. Run the following command in your terminal to generate one and save it for later.

```sh
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### All Variables Needed

Set up the following environment variables anywhere in your shell initialization file _(i.e. `.bashrc` or `.zshrc`)_.

```sh
export LEARN_OPS_DB=learnopsdev
export LEARN_OPS_USER=learnopsdev
export LEARN_OPS_PASSWORD=DatabasePasswordOfYourChoice
export LEARN_OPS_HOST=127.0.0.1
export LEARN_OPS_PORT=5432
export LEARN_OPS_CLIENT_ID=GithubOAuthAppClientId
export LEARN_OPS_SECRET_KEY=GithubOAuthAppSecret
export LEARN_OPS_DJANGO_SECRET_KEY="GeneratedDjangoSecretKey"
export LEARN_OPS_ALLOWED_HOSTS="127.0.0.1,localhost,web"
export LEARN_OPS_SUPERUSER_NAME=AdminUsernameOfYourChoice
export LEARN_OPS_SUPERUSER_PASSWORD=AdminPasswordOfYourChoice
```

### Activate Environment Variables

Then reload your bash session with `source ~/.zshrc` if you are using zshell or `source ~/.bashrc` if you have the default bash environment.

### Install Docker
1. Install Docker Desktop for your machine https://docs.docker.com/desktop/
2. Once installation is complete, run `docker compose up --build`


## Testing the Installation

1. The API should be running after step 2 above (`docker compose up --build`).
1. Visit http://localhost:8000/admin
1. Authenticate with the superuser credentials you created previously and then you can view all kinds of data that is in your database.

Move onto the front end repo and follow the instructions in that README

### ERD

[dbdiagram.io ERD](https://dbdiagram.io/d/6005cc1080d742080a36d6d8)
