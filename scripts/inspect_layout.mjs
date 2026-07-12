#!/usr/bin/env node

import puppeteer from "puppeteer";

const [url, widthText = "390", heightText = "844"] = process.argv.slice(2);
const browser = await puppeteer.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--allow-file-access-from-files"],
});
const page = await browser.newPage();
await page.setViewport({ width: Number(widthText), height: Number(heightText), deviceScaleFactor: 1 });
await page.goto(url, { waitUntil: "networkidle0" });
const result = await page.evaluate(() => {
  const selectors = ["html", "body", ".md-main", ".md-main__inner", ".md-content", ".md-content__inner", ".md-typeset", ".md-typeset p", ".book-diagram", ".book-diagram picture", ".book-diagram img"];
  return {
    viewport: { width: innerWidth, documentWidth: document.documentElement.scrollWidth },
    elements: Object.fromEntries(
      selectors.map((selector) => {
        const element = document.querySelector(selector);
        if (!element) return [selector, null];
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return [
          selector,
          {
            left: rect.left,
            right: rect.right,
            width: rect.width,
            marginLeft: style.marginLeft,
            marginRight: style.marginRight,
            paddingLeft: style.paddingLeft,
            paddingRight: style.paddingRight,
            overflowX: style.overflowX,
          },
        ];
      }),
    ),
  };
});
console.log(JSON.stringify(result, null, 2));
await browser.close();
