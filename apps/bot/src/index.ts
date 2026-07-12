import { createBot } from "./bot";

const token = process.env.BOT_TOKEN;
if (!token) {
  throw new Error("BOT_TOKEN is not set");
}

const bot = createBot(token);

bot.start({
  onStart: (info) => console.log(`UltimaHost bot started as @${info.username}`),
});
