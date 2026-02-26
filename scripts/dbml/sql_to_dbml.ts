/**
 * sql_to_dbml.ts
 *
 * Reads schema/db.sql (PostgreSQL DDL) and writes schema/db.dbml using @dbml/core.
 *
 * Usage:
 *   npx ts-node sql_to_dbml.ts [--sql <path>] [--dbml <path>]
 *
 * Defaults:
 *   --sql  ../../schema/db.sql
 *   --dbml ../../schema/db.dbml
 */

import * as fs from "fs";
import * as path from "path";
import { importer } from "@dbml/core";

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const DEFAULT_SQL = path.join(REPO_ROOT, "schema", "db.sql");
const DEFAULT_DBML = path.join(REPO_ROOT, "schema", "db.dbml");

function parseArgs(): { sql: string; dbml: string } {
  const args = process.argv.slice(2);
  let sql = DEFAULT_SQL;
  let dbml = DEFAULT_DBML;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--sql" && args[i + 1]) sql = path.resolve(args[++i]);
    else if (args[i] === "--dbml" && args[i + 1]) dbml = path.resolve(args[++i]);
  }
  return { sql, dbml };
}

function main(): void {
  const { sql: sqlPath, dbml: dbmlPath } = parseArgs();

  if (!fs.existsSync(sqlPath)) {
    console.error(`Error: SQL file not found: ${sqlPath}`);
    process.exit(1);
  }

  const sql = fs.readFileSync(sqlPath, "utf-8");

  let dbml: string;
  try {
    dbml = importer.import(sql, "postgres");
  } catch (err) {
    console.error("Error parsing SQL:", err);
    process.exit(1);
  }

  const header = [
    "// DBML schema for elogfetch",
    "// Auto-generated from schema/db.sql via scripts/dbml/sql_to_dbml.ts",
    "// DO NOT EDIT MANUALLY — run `make schema` to regenerate.",
    "",
    "",
  ].join("\n");

  fs.mkdirSync(path.dirname(dbmlPath), { recursive: true });
  fs.writeFileSync(dbmlPath, header + dbml);

  const relSql = path.relative(REPO_ROOT, sqlPath);
  const relDbml = path.relative(REPO_ROOT, dbmlPath);
  console.log(`Converted ${relSql} → ${relDbml}`);
}

main();
