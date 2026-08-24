const assert = require("node:assert/strict");
const test = require("node:test");

const { setupPublicNav } = require("../assets/js/public-nav.js");

class FakeEventTarget {
  constructor() {
    this.listeners = new Map();
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) || [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  dispatch(type, event = {}) {
    const payload = {
      key: "",
      target: this,
      prevented: false,
      preventDefault() {
        this.prevented = true;
      },
      ...event,
    };
    (this.listeners.get(type) || []).forEach((listener) => listener(payload));
    return payload;
  }
}

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  contains(value) {
    return this.values.has(value);
  }

  toggle(value, force) {
    if (force) {
      this.values.add(value);
    } else {
      this.values.delete(value);
    }
  }
}

function createGroup(name) {
  const trigger = new FakeEventTarget();
  trigger.attributes = new Map([["aria-expanded", "false"]]);
  trigger.focused = false;
  trigger.getAttribute = (key) => trigger.attributes.get(key) || null;
  trigger.setAttribute = (key, value) => trigger.attributes.set(key, value);
  trigger.focus = () => {
    trigger.focused = true;
  };

  const links = [new FakeEventTarget(), new FakeEventTarget()];
  links.forEach((link) => {
    link.focused = false;
    link.focus = () => {
      link.focused = true;
    };
  });
  const menu = {
    hidden: true,
    querySelectorAll(selector) {
      return selector === "a[href]" ? links : [];
    },
  };
  const group = {
    name,
    classList: new FakeClassList(),
    querySelector(selector) {
      if (selector === "[data-nav-trigger]") return trigger;
      if (selector === "[data-nav-menu]") return menu;
      return null;
    },
  };
  return { group, links, menu, trigger };
}

function fixture() {
  const first = createGroup("servers");
  const second = createGroup("community");
  const nav = new FakeEventTarget();
  nav.querySelectorAll = () => [first.group, second.group];
  nav.contains = (target) => target !== "outside";
  const ownerDocument = new FakeEventTarget();
  setupPublicNav(nav, ownerDocument);
  return { first, nav, ownerDocument, second };
}

test("click toggles a dropdown and opening another closes the first", () => {
  const { first, second } = fixture();
  first.trigger.dispatch("click");
  assert.equal(first.trigger.getAttribute("aria-expanded"), "true");
  assert.equal(first.menu.hidden, false);

  second.trigger.dispatch("click");
  assert.equal(first.trigger.getAttribute("aria-expanded"), "false");
  assert.equal(first.menu.hidden, true);
  assert.equal(second.trigger.getAttribute("aria-expanded"), "true");
});

test("Escape closes the open dropdown and restores trigger focus", () => {
  const { first, nav } = fixture();
  first.trigger.dispatch("click");
  const event = nav.dispatch("keydown", { key: "Escape" });
  assert.equal(event.prevented, true);
  assert.equal(first.menu.hidden, true);
  assert.equal(first.trigger.focused, true);
});

test("click outside closes all dropdowns", () => {
  const { first, ownerDocument } = fixture();
  first.trigger.dispatch("click");
  ownerDocument.dispatch("click", { target: "outside" });
  assert.equal(first.trigger.getAttribute("aria-expanded"), "false");
  assert.equal(first.menu.hidden, true);
});

test("Arrow keys open a menu and focus an edge without trapping Tab", () => {
  const { first } = fixture();
  const arrowEvent = first.trigger.dispatch("keydown", { key: "ArrowDown" });
  assert.equal(arrowEvent.prevented, true);
  assert.equal(first.links[0].focused, true);

  const tabEvent = first.trigger.dispatch("keydown", { key: "Tab" });
  assert.equal(tabEvent.prevented, false);
});
