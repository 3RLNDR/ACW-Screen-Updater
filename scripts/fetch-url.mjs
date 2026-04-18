import fs from 'node:fs/promises';
import process from 'node:process';

const args = process.argv.slice(2);
const url = args[0];

if (!url) {
  console.error('Usage: node fetch-url.mjs <url> [--out <path>]');
  process.exit(1);
}

let outPath = null;
for (let index = 1; index < args.length; index += 1) {
  if (args[index] === '--out') {
    outPath = args[index + 1] ?? null;
    index += 1;
  }
}

if (args.includes('--out') && !outPath) {
  console.error('Missing output path after --out');
  process.exit(1);
}

const response = await fetch(url, {
  headers: {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36',
    'Accept-Language': 'en-GB,en;q=0.9'
  },
  redirect: 'follow'
});

if (!response.ok) {
  console.error(`Request failed with ${response.status} ${response.statusText}`);
  process.exit(1);
}

if (outPath) {
  const buffer = Buffer.from(await response.arrayBuffer());
  await fs.writeFile(outPath, buffer);
} else {
  process.stdout.write(await response.text());
}
