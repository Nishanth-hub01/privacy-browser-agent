import { JSDOM } from "jsdom";
import { detectSensitiveDOM } from "./domDetector";

const html = `
  <form>
    <input type="text" name="name" placeholder="Full Name">
    <input type="email" name="email" placeholder="Email Address">
    <input type="password" name="password" placeholder="Password">
    <input type="tel" name="phone" placeholder="Phone Number">
    <input type="text" name="address" placeholder="Home Address">
  </form>
`;

const dom = new JSDOM(html);

const findings = detectSensitiveDOM(dom.window.document);

console.log("DOM Privacy Findings:");
console.log(findings);