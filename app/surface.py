from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from .models import Locator


class SurfaceError(Exception):
    pass


class BrowserSurface:
    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    def observe(self) -> list[dict[str, Any]]:
        script = """
        () => {
          const els = Array.from(document.querySelectorAll(
            'input,button,a,select,textarea,[role],h1,h2,h3,[data-testid]'
          ));
          return els.map((el, i) => {
            const label = el.labels && el.labels.length
              ? Array.from(el.labels).map(x => x.innerText.trim()).join(" ")
              : null;
            const role = el.getAttribute("role") ||
              ({INPUT:"textbox", TEXTAREA:"textbox", BUTTON:"button", A:"link", SELECT:"combobox"}[el.tagName] || null);
            const name = el.getAttribute("aria-label") ||
              label ||
              el.getAttribute("placeholder") ||
              (el.innerText || "").trim().replace(/\\s+/g, " ").slice(0, 120);
            return {
              index: i,
              tag: el.tagName.toLowerCase(),
              role,
              name: name || null,
              label,
              text: (el.innerText || "").trim().replace(/\\s+/g, " ").slice(0, 160),
              test_id: el.getAttribute("data-testid"),
              value: el.value ?? null
            };
          }).filter(x => x.role || x.name || x.text);
        }
        """
        return self.page.evaluate(script)

    def locator_for(self, locator: Locator):
        if locator.test_id:
            return self.page.get_by_test_id(locator.test_id)
        if locator.role and locator.name:
            return self.page.get_by_role(locator.role, name=locator.name, exact=True)
        if locator.label:
            return self.page.get_by_label(locator.label, exact=True)
        if locator.text:
            return self.page.get_by_text(locator.text, exact=True)
        raise SurfaceError("Artifact contains no usable locator")

    def target_by_index(self, index: int):
        elements = self.page.locator("input,button,a,select,textarea,[role],h1,h2,h3,[data-testid]")
        return elements.nth(index)

    def click(self, target: Locator | None = None, index: int | None = None) -> None:
        loc = self.locator_for(target) if target else self.target_by_index(index)
        loc.click()

    def type(self, value: str, target: Locator | None = None, index: int | None = None) -> None:
        loc = self.locator_for(target) if target else self.target_by_index(index)
        loc.fill(value)

    def extract(self, target: Locator | None = None, index: int | None = None) -> str:
        loc = self.locator_for(target) if target else self.target_by_index(index)
        return (loc.inner_text() if loc.evaluate("(e) => e.tagName !== 'INPUT'") else loc.input_value()).strip()

    def screenshot(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=path, full_page=True)

    def visible_text(self) -> str:
        return self.page.locator("body").inner_text()

    def wait_for_text(self, text: str, timeout: int = 5000) -> bool:
        try:
            self.page.get_by_text(text, exact=False).wait_for(timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    def install_human_event_logger(self, endpoint: str) -> None:
        self.page.evaluate(
            """
            (endpoint) => {
              window.__humanLogging = true;
              document.addEventListener('click', e => {
                if (!window.__humanLogging) return;
                fetch(endpoint, {
                  method: 'POST',
                  headers: {'Content-Type':'application/json'},
                  body: JSON.stringify({
                    type:'click',
                    text:(e.target.innerText || e.target.getAttribute('aria-label') || '').slice(0,100),
                    tag:e.target.tagName
                  })
                }).catch(()=>{});
              }, true);
              document.addEventListener('input', e => {
                if (!window.__humanLogging) return;
                fetch(endpoint, {
                  method: 'POST',
                  headers: {'Content-Type':'application/json'},
                  body: JSON.stringify({
                    type:'input',
                    tag:e.target.tagName,
                    field:e.target.getAttribute('aria-label') || e.target.getAttribute('name') || e.target.id || ''
                  })
                }).catch(()=>{});
              }, true);
            }
            """,
            endpoint,
        )
