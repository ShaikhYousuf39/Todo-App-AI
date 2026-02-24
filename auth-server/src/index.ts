import { betterAuth } from "better-auth";
import { bearer } from "better-auth/plugins";
import { createServer } from "http";
import { Pool } from "pg";
import "dotenv/config";

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL?.includes("sslmode=require")
    ? { rejectUnauthorized: false }
    : undefined,
});

// Initialize Better Auth
export const auth = betterAuth({
  database: pool,
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3001",
  plugins: [bearer()],
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // 1 day
    cookieCache: {
      enabled: true,
      maxAge: 60 * 5, // 5 minutes
    },
  },
  trustedOrigins: [
    process.env.FRONTEND_URL || "http://localhost:5173",
    "http://localhost:5173",
  ],
});

// CORS headers
const corsHeaders = {
  "Access-Control-Allow-Origin": process.env.FRONTEND_URL || "http://localhost:5173",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Allow-Credentials": "true",
};

// Create HTTP server
const server = createServer(async (req, res) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    res.writeHead(204, corsHeaders);
    res.end();
    return;
  }

  // Add CORS headers to all responses
  Object.entries(corsHeaders).forEach(([key, value]) => {
    res.setHeader(key, value);
  });

  // Health check endpoint
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));
    return;
  }

  // Handle Better Auth routes
  if (req.url?.startsWith("/api/auth")) {
    try {
      // Convert Node.js request to Web Request
      const url = new URL(req.url, `http://${req.headers.host}`);
      const headers = new Headers();
      Object.entries(req.headers).forEach(([key, value]) => {
        if (value) headers.set(key, Array.isArray(value) ? value[0] : value);
      });

      let body: string | undefined;
      if (req.method !== "GET" && req.method !== "HEAD") {
        body = await new Promise<string>((resolve) => {
          let data = "";
          req.on("data", (chunk) => (data += chunk));
          req.on("end", () => resolve(data));
        });
      }

      const webRequest = new Request(url.toString(), {
        method: req.method,
        headers,
        body: body || undefined,
      });

      // Handle auth request
      const response = await auth.handler(webRequest);

      // Convert Web Response to Node.js response
      const responseHeaders = Object.fromEntries(
        Array.from(response.headers.entries()).filter(([key]) => key.toLowerCase() !== "set-cookie")
      );
      const setCookies =
        typeof (response.headers as any).getSetCookie === "function"
          ? (response.headers as any).getSetCookie()
          : [];

      const outgoingHeaders: Record<string, string | string[]> = {
        ...responseHeaders,
        ...corsHeaders,
      };
      if (setCookies.length > 0) {
        // Better Auth can emit multiple cookies; preserve them all.
        outgoingHeaders["Set-Cookie"] = setCookies;
      }

      res.writeHead(response.status, outgoingHeaders);
      const responseBody = await response.text();
      res.end(responseBody);
    } catch (error) {
      console.error("Auth error:", error);
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Internal server error" }));
    }
    return;
  }

  // 404 for other routes
  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "Not found" }));
});

const PORT = parseInt(process.env.PORT || "3001", 10);

server.listen(PORT, () => {
  console.log(`Auth server running on http://localhost:${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Auth API: http://localhost:${PORT}/api/auth/*`);
});
