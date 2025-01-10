import { serve } from "bun";

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1";

interface ErrorResponse {
  error: {
    type: string;
    message: string;
  };
}

const server = serve({
  port: 8010,
  async fetch(req: Request) {
    // Handle preflight requests
    if (req.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers":
            "Content-Type, Anthropic-Version, x-api-key",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    // Only handle requests to /proxy/v1/messages
    const url = new URL(req.url);
    if (url.pathname !== "/proxy/v1/messages") {
      return new Response(
        JSON.stringify({
          error: { type: "invalid_request", message: "Invalid endpoint" },
        } satisfies ErrorResponse),
        { status: 404 },
      );
    }

    // Only allow POST requests
    if (req.method !== "POST") {
      return new Response(
        JSON.stringify({
          error: { type: "invalid_request", message: "Method not allowed" },
        } satisfies ErrorResponse),
        { status: 405 },
      );
    }

    try {
      // Forward the request to Anthropic API
      const response = await fetch(`${ANTHROPIC_API_URL}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Anthropic-Version":
            req.headers.get("Anthropic-Version") || "2023-06-01",
          "x-api-key": req.headers.get("x-api-key") || "",
        },
        body: await req.text(),
      });

      // Forward the response back to the client
      const responseData = await response.json();
      return new Response(JSON.stringify(responseData), {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    } catch (error) {
      console.error("Proxy error:", error);
      return new Response(
        JSON.stringify({
          error: { type: "proxy_error", message: "Failed to proxy request" },
        } satisfies ErrorResponse),
        {
          status: 500,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        },
      );
    }
  },
});

console.log(`Proxy server listening on http://localhost:${server.port}`);
