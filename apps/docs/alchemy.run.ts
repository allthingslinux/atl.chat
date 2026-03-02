import alchemy from "alchemy";
import { Nextjs } from "alchemy/cloudflare";

const app = await alchemy("atl-chat");

export const website = await Nextjs("docs", {
  domains: ["docs.atl.chat"],
});

console.log({ url: website.url });

await app.finalize();
