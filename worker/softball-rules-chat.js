// Cloudflare Worker: Sunshine on a Ranney Day softball chat (Workers AI, no API key needed)
// The website sends everything the bot needs in `context`: the current rulebook
// (data/rules.json), standings, schedule, scores, box scores and stats.
// To change the rules, edit data/rules.json in the site repo. No worker change needed.

const MODEL = '@cf/meta/llama-3.3-70b-instruct-fp8-fast';
const MAX_CONTEXT_CHARS = 40000;

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': 'https://pranney82.github.io',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS_HEADERS });
    if (request.method !== 'POST') return new Response('Method not allowed', { status: 405, headers: CORS_HEADERS });

    try {
      const { messages, context } = await request.json();

      if (!Array.isArray(messages) || messages.length === 0) return json({ error: 'No messages provided' }, 400);
      if (messages.length > 20) return json({ error: 'Conversation too long. Please refresh and start a new chat.' }, 400);

      const clean = messages
        .filter(m => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
        .map(m => ({ role: m.role, content: m.content.slice(0, 2000) }));

      let systemPrompt = `You are the assistant on the Sunshine on a Ranney Day (SOARD) men's slow pitch softball team website. The coach is Ranney. The team plays in the Cherokee Recreation & Parks (CRPA) Wednesday men's slow pitch league, where the league site lists the team as "Driven". The team used to be called Drive Auto Repair.

You answer questions about:
- League rules (mercy rule, home run limits, rosters, pickup players, pitching, bats, uniforms, playoffs, tiebreakers)
- Standings, scores, the schedule and upcoming games
- Player batting stats (season and career) and box scores

Answer only from the SITE DATA below. The LEAGUE RULES section there is the current rulebook and overrides anything you think you know about softball rules. If the data does not cover a question, say so instead of guessing. Keep answers short: 2-3 sentences unless the question needs more. Be friendly and direct, like a teammate who knows the rulebook.`;

      if (typeof context === 'string' && context.trim()) {
        systemPrompt += `\n\nSITE DATA:\n${context.slice(0, MAX_CONTEXT_CHARS)}`;
      }

      const result = await env.AI.run(MODEL, {
        messages: [{ role: 'system', content: systemPrompt }, ...clean],
        max_tokens: 600,
      });

      const reply = (result && (result.response || (result.choices && result.choices[0] && result.choices[0].message && result.choices[0].message.content))) || '';
      if (!reply) return json({ error: 'Empty reply from model' }, 502);
      return json({ reply });
    } catch (err) {
      return json({ error: 'Server error: ' + err.message }, 500);
    }
  },
};
