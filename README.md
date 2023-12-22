# ai-evaluator-extension ![deployment automatic](https://img.shields.io/badge/deployment-automatic-success)

Airtable extension for evaluating application to our courses using AI, specifically large language models (LLMS).

## Developer setup

To start developing this extension:

1. Clone this git repository
2. Install [Node.js](https://nodejs.org/)
3. Run `npm install`
4. Run `npm start` (for the 'Applications' base in the BlueDot Impact AirTable account)
5. Load the relevant base
6. Make changes to the code and see them reflected in the app!

If the changes don't appear to be updating the app, try clicking the extension name then 'Edit extension', then pasting in the server address printed to the console from step 4 (probably `https://localhost:9000`).

Changes merged into the default branch will automatically be deployed. You can manually deploy new versions using `npm run deploy`. If you get the error `airtableApiBlockNotFound`, set up the block CLI with `npx block set-api-key` with a [personal access token](https://airtable.com/developers/web/guides/personal-access-tokens).

If you want to install this on a new base see [these instructions](https://www.airtable.com/developers/apps/guides/run-in-multiple-bases).
