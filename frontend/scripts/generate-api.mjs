import { readFile, writeFile, mkdir } from "node:fs/promises";
import openapiTS, { astToString } from "openapi-typescript";
const url = process.env.OPENAPI_URL;
const schema = url
  ? await (await fetch(url)).json()
  : JSON.parse(
      await readFile(new URL("../openapi.json", import.meta.url), "utf8"),
    );
if (schema.openapi == null || !schema.paths?.["/ask"])
  throw new Error("Invalid FastAPI schema");
await mkdir(new URL("../src/api/generated/", import.meta.url), {
  recursive: true,
});
await writeFile(
  new URL("../src/api/generated/schema.d.ts", import.meta.url),
  astToString(await openapiTS(schema, { defaultNonNullable: false })),
);
if (url)
  await writeFile(
    new URL("../openapi.json", import.meta.url),
    JSON.stringify(schema, null, 2) + "\n",
  );
console.log(
  "Generated API types from " +
    (url ? "live OpenAPI" : "checked-in OpenAPI snapshot"),
);
