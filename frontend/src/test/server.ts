import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { accountData, email, inbox, supported, taskPage } from "./fixtures";
export const base = "http://localhost:5173/api";
export const server = setupServer(
  http.get(base + "/tasks", () => HttpResponse.json(taskPage)),
  http.get(base + "/gmail/accounts", () => HttpResponse.json(accountData)),
  http.get(base + "/emails", () => HttpResponse.json(inbox)),
  http.get(base + "/emails/:id", () => HttpResponse.json(email)),
  http.get(base + "/search/semantic", () =>
    HttpResponse.json({
      query: "test",
      count: 1,
      results: [
        { email, score: 0.8, matched_text: "Original matched source text" },
      ],
    }),
  ),
  http.post(base + "/ask", () => HttpResponse.json(supported)),
);
