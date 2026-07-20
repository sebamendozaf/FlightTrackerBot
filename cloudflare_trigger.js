// Cloudflare Worker — dispara check_flights.yml cada 15 minutos
// Configurar en: dash.cloudflare.com → Workers & Pages → flight-trigger
//
// Variables requeridas (Settings → Variables and secrets):
//   GITHUB_TOKEN  — Personal Access Token con scope "workflow"
//
// Cron trigger (Settings → Trigger events):
//   */15 * * * *

export default {
  async scheduled(event, env) {
    await fetch(
      "https://api.github.com/repos/sebamendozaf/FlightTrackerBot/actions/workflows/check_flights.yml/dispatches",
      {
        method: "POST",
        headers: {
          Authorization: `token ${env.GITHUB_TOKEN}`,
          Accept: "application/vnd.github.v3+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ref: "main" }),
      }
    );
  },
};
