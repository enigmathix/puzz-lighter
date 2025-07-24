# 🚀 Puzz Lighter

**Puzz Lighter** is a lightweight Python framework for running puzzle hunts. Its main advantage over other frameworks like [gph-site](https://github.com/galacticpuzzlehunt/gph-site) lies in its simplicity and low cost (free in most cases):

- Runs on Google Cloud, a proven, reliable provider with near 100% uptime  
- Uses Flask instead of Django, resulting in a smaller memory footprint  
- Uses Google Cloud Datastore (NoSQL) instead of an RDBMS for fast database access  
- Leverages daily quotas, making it likely to run for free all year long  

**Puzz Lighter** offers the following features:

- Passwordless team login (email optional but recommended)  
- Stealth mode to participate without appearing on the leaderboard  
- Guest account to browse puzzles after the hunt ends  
- Interface to submit suspected errata  
- Puzzle/round unlocks based on specific solves, solve count, or time  
- Ability to link a Google Sheet to each puzzle  
- Timed hints (an interface for hint requests could be added)  
- Limited number of guesses on a sliding 24-hour window  
- Support for defining tokens visible to puzzle solvers  
- Puzzle solution published as soon as it's solved  
- Option to hide solutions to preserve original conditions for late teams  
- Puzzle solve notifications sent to teams  
- Support for running multiple hunts on the same server  
- Admin interface to monitor and manage the hunt  

You can see it in action in Edric's [2025 Truzzle Hunt](https://2025truzzlehunt.happinessboard.com/). That hunt had over 1,000 users (around 400 simultaneously) and cost only $0.25 to run. Since then, improvements have been made to further reduce that cost.

---

## Installation

- Requirement: Python 3  
- Install the [gcloud SDK](https://cloud.google.com/sdk/docs/install)  
- Clone this repo: `git clone ...`  
- In the repo directory, run: `pip install -r requirements.txt`

---

## Configuration

### Google App Engine

Start by running `gcloud init` to set up your account and project.

In the [Google Cloud Console](https://cloud.google.com/), create a **Python Standard App Engine** (not Flexible).

To create the datastore, go to [Datastore](https://console.cloud.google.com/datastore), click **Create Database**, and pick **Standard Edition** and **Firestore with Datastore compatibility** (*not* a Firestore Native database)

> ⚠️ The location you pick is permanent. Prices beyond the free quota vary by location; `us-east4` is typically a good choice.

Edit the `app` script to set:

- `GOOGLE_CLOUD_PROJECT`: your project ID  
- `HUNT`: the hunt slug (used locally only)  
- `PORT`: port number (used locally only)  
- Check that the paths for Python 3 and `dev_appserver.py` match your system  

In `app.yaml` (the App Engine config file), fill in the `env_variables` section:

- `SECRET_KEY`: used by Flask for sessions  
- `FIREBASE_URL`: see Firebase section below  
- `CAPTCHA_KEY` and `CAPTCHA_SECRET_KEY`: see reCAPTCHA section below  
- `EMAIL_ADDRESS`: sender email for lost keys  
- `GCLOUD_EMAIL_ADDRESS`: service account email for sending errata (recommended for higher quota)  
- `DOMAIN`: optional, used in the admin view  
- `CDN`: see CDN section below  

---

### Firebase

Go to the [Firebase Console](https://console.firebase.google.com/) and:

1. Create a project  
2. Choose **Realtime Database** (not Firestore) under the *Build* menu  
3. In the *Data* tab, copy the reference URL (e.g., `https://...firebaseio.com`) and paste it into `FIREBASE_URL` in `app.yaml`  
4. In the *Rules* tab, replace and publish the following:

    ```json
    {
      "rules": {
        "$hunt": {
          ".read": "auth != null && auth.uid === 'admin'",
          "$team": {
            ".read": true,
            ".write": false
          }
        }
      }
    }
    ```

    > This allows teams to read their own entry for notifications, while only admin can read everything.

5. In *Project Overview* ⚙️. *Project Settings*.. *General*, add an app of type **Web App** `</>` and register it. In the *Firebase SDK* section under `Use a <script>` tag or *Under the Config* checkbox, copy the block:

    ```js
    const firebaseConfig = {
      (...)
    }
    ```

    Paste this into your `static/notify.js` file.

6. In *Project Settings* → *Service Accounts*, click **Generate new private key**, download the JSON file, and save it as `firebase.json` in your main directory. Update `FIREBASE_URL` in `app.yaml` to point to `'firebase.json'`.

7. Under *Build* → *Authentication*, click **Get Started**. That's it. This is used to authenticate the admin interface.

> 🔄 The Spark plan allows only 100 simultaneous connections — not enough for a hunt. Upgrade to the **Blaze plan**. It's still free within generous quotas. During the Truzzle Hunt, only half the *Downloads* daily quota was used.

---

### reCAPTCHA

Used to prevent brute-force key guessing on the *register* and *login* pages.

1. Go to the [reCAPTCHA console](https://console.cloud.google.com/security/recaptcha)  
2. Create a key of type **Web**, add your domain and `localhost`  
3. Copy the key ID to `CAPTCHA_KEY` in `app.yaml`  
4. In *Key Details* → *Integration*, choose **Use legacy key**, and copy it into `CAPTCHA_SECRET_KEY`

---

### CDN

I recommend using [Cloudflare](https://www.cloudflare.com/) to serve static files and reduce App Engine bandwidth usage (limited to 1 GB/day).

1. Host your static files in a separate GitHub or GitLab repo  
2. In Cloudflare → *Compute (Workers)* → *Workers & Pages*, click **Create**, choose the *Pages* tab (*not Workers*)
3. Ignore the recommendation. *Import an existing Git Repository* and follow the instructions  
4. In the *Custom domains* tab, add your subdomain name and follow the instructions  
5. Set `CDN` in `app.yaml` to the subdomain URL  
6. Move your `static/` files into the CDN repo  
7. Create a soft link from your app’s `static` directory to the CDN repo  
8. Add `static` to your `.gitignore` and `.gcloudignore`

---

## Running

To run the server locally:
`./app run`

To deploy to Google Cloud:
`./app deploy`

After the first deployment, create datastore indexes:
`./app index`

Puzz Lighter supports multiple hunts on the same server. It determines the hunt from the subdomain. In development, the `HUNT` environment variable sets this.

---

## Datastore

To create a hunt, visit the admin interface:

- Locally: `http://localhost:8042/admin` (check *Sign in as Administrator* in the popup)
- Live: `https://<your-domain>/admin` (Sign in using your Google account)

You’ll see a form like this:

- **Hunt**
  - `Slug`: `sample`
  - `Name`: `Sample Hunt`
  - `Start` and `End`: date/time when the hunt opens/closes

You can create rounds and puzzles through the admin interface, or you can write a script (e.g. `populate-sample.py`) to define them programmatically. To load data from the script, visit:

- Locally: `http://localhost:8042/adminpopulate/sample`
- Live: `https://<your-domain>/adminpopulate/sample`


Each hunt's `slug` is used as a **namespace**, so all puzzle data is isolated per hunt. The only global entity is the `Hunt` itself.

---

## Scaling & Quota

Google App Engine runs on **instances** (virtual machines). The free daily allocation includes:

- **28 instance-hours** on an `F1` class machine (384 MB memory)
  - 1 instance running 24/7
  - +1 instance running for 4 extra hours (e.g. during traffic spikes)

#### Example: Truzzle Hunt

- A second instance was automatically deployed during the first 15 minutes of the hunt.
- After that, a single instance handled all traffic.
- **Total cost: $0**

This is configured in `app.yaml`:

```yaml
automatic_scaling:
  max_instances: 2
  max_idle_instances: 1
```

Each instance handles up to **8 parallel requests**. To reduce memory usage, requests are split between 2 workers of 4 threads each:

`entrypoint: gunicorn -b :$PORT --workers 2 --threads 4 main:app`

- Memory usage during the Truzzle Hunt: ~50% of the available 384 MB
- No significant slowdowns, except for the first 45 seconds (before the second instance started)

### Bandwidth

- Bandwidth usage stayed below the daily quota thanks to the use of a **CDN**.
- Without a CDN, the daily **1 GB static file** quota would likely be exceeded.
- **Cost: $0**

### Datastore

Google Cloud Datastore has three types of usage quotas:

- **Reads**: 50,000 per day (free)
- **Writes**: 20,000 per day (free)
- **Small reads**: used by queries, counted under reads

#### Writes

- Writes were well below the quota.
- Most data is static during a hunt:
  - Rounds and puzzles don't change
  - Teams are updated only when they solve puzzles
- **Cost: $0**

#### Reads

- Reads are triggered on every page visit to:
  - Query rounds and puzzles
  - Read puzzle and round data
  - Authenticate and check team state
- The number of reads **slightly exceeded the free quota** during the Truzzle Hunt.
- **Total cost: $0.25**

To reduce future read costs, a **memcache layer** (free to use) has been added to cache datastore entities. This should eliminate most excess reads and bring total cost closer to **$0**.
