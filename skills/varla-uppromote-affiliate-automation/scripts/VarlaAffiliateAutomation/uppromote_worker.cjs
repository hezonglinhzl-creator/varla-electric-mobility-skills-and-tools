const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

const RUN_STARTED_AT = Date.now();
const CLICK_RESPONSE_TIMEOUT_MS = 7000;

function cleanText(value) {
  return String(value ?? '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function affiliateRowMatches(rowText, email) {
  return cleanText(rowText).split(' ').includes(cleanText(email));
}

function chooseDetailNavigation({ url, bodyText, targetEmail }) {
  const couponPage = /\/affiliates\/[^/]+\/coupons(?:[/?#]|$)/i.test(String(url || ''));
  return couponPage && cleanText(bodyText).includes(cleanText(targetEmail)) ? 'inline' : 'list';
}

function assignedCouponsAction(bodyText, code) {
  const body = cleanText(bodyText);
  if (body.includes(cleanText(code))) return 'existing';
  if (body.includes('assigned coupons will show here')) return 'add';
  return 'wait';
}

function couponPageEntryAction() {
  return 'add';
}

function couponSaveVerified(bodyText, code) {
  const body = cleanText(bodyText);
  if (body.includes('unsaved changes')) return false;
  return body.includes(cleanText(code))
    || body.includes('coupon assigned')
    || body.includes('coupon created successfully');
}

function combinationCheckboxSelectors(name) {
  return [
    `xpath=//*[not(*) and normalize-space(.)="${name}"]/ancestor::div[contains(@class,"_container_")][1]//input[@type="checkbox"]`,
    `xpath=//*[normalize-space()="${name}"]/ancestor::label[1]//input[@type="checkbox"]`,
    `xpath=//*[normalize-space()="${name}"]/ancestor::*[contains(@class,"checkbox-wrapper")][1]//input[@type="checkbox"]`,
  ];
}

function isAffiliateListUrl(value) {
  try {
    const pathname = new URL(String(value)).pathname.replace(/\/+$/, '');
    return pathname.endsWith('/admin/affiliates');
  } catch {
    return false;
  }
}

function affiliateListEntryAction(stage) {
  return stage === 'affiliate_create' ? 'resume' : 'refresh';
}

function isValidShortLink(value) {
  try {
    const url = new URL(String(value));
    return url.protocol === 'https:' && Boolean(url.hostname);
  } catch {
    return false;
  }
}

function uniqueBy(items, keyFn) {
  const seen = new Set();
  return items.filter(item => {
    const key = keyFn(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function makeResult(shortLink, affiliateExisted, savedLinkVerified) {
  return {
    status: 'complete',
    affiliate: affiliateExisted ? 'existing_verified' : 'created_verified',
    coupon: 'verified',
    shortLink,
    savedLinkVerified,
  };
}

function isAppReadySnapshot(snapshot) {
  return Boolean(snapshot.hasSearch || snapshot.hasAddAffiliate);
}

function isGeneratedAffiliateLink(value, destination) {
  return isValidShortLink(value) && String(value) !== String(destination);
}

function extractShortLink(textValue) {
  const match = String(textValue || '').match(/https:\/\/(?:bit\.ly|tinyurl\.com|t\.co)\/[A-Za-z0-9_-]+/);
  return match ? match[0] : '';
}

function shortLinkEntryAction() {
  return 'generate';
}

function regenerateLinkPlan(enabled) {
  return enabled ? ['affiliate', 'detail', 'login', 'short_link'] : null;
}

function shouldSearchAffiliateScope(isMainFrame, hasSearch, hasAdd) {
  return Boolean(hasSearch || hasAdd);
}

function regenerateAffiliateAction(found) {
  return found ? 'continue' : 'stop';
}

function affiliateDashboardReady(bodyText, hasProductLink, creatorName, creatorCode) {
  const body = cleanText(bodyText);
  const matchesCreator = body.includes(cleanText(creatorName)) || body.includes(cleanText(creatorCode));
  return Boolean(matchesCreator && hasProductLink);
}

function firstRowMatchesTarget(rowText, email) {
  return affiliateRowMatches(rowText, email);
}

async function firstAffiliateRow(page) {
  for (const frame of scopes(page)) {
    const rows = frame.locator('tbody tr');
    if (await rows.count().catch(() => 0)) return rows.first();
  }
  return null;
}

function classifyWorkflowSnapshot(snapshot) {
  const body = cleanText(snapshot.bodyText);
  const email = cleanText(snapshot.targetEmail);
  const code = cleanText(snapshot.targetCode);
  // Short/generic codes such as LINK, Karl, or owc frequently occur in normal
  // page copy. Only use a code as resume evidence when it is distinctive;
  // exact email remains the strongest ownership proof on admin pages.
  const matchesTarget = (email && body.includes(email)) || (code.length >= 5 && body.includes(code));
  if (!matchesTarget) return 'affiliate_list';
  if (snapshot.hasProductLinkModal) return 'short_link_modal';
  if (body.includes('manage coupons')) return 'coupon_form';
  if (body.includes('login as affiliate') && body.includes(email)) return 'affiliate_detail';
  if (String(snapshot.url).includes('/affiliates/create')) return 'affiliate_create';
  if (body.includes('get product link')) return 'affiliate_dashboard';
  return 'affiliate_list';
}

function prioritizeCandidates(candidates) {
  return uniqueBy([...candidates].sort((a, b) => {
    const envOrder = Number(b.source === 'env') - Number(a.source === 'env');
    return envOrder || b.mtime - a.mtime;
  }), item => item.port);
}

function isExactCollectionCandidate(value, target) {
  return cleanText(value) === cleanText(target);
}

function makeProgress(stage, status, elapsedMs = Date.now() - RUN_STARTED_AT) {
  return { stage, status, elapsedMs };
}

function emitProgress(stage, status) {
  process.stdout.write(`VARLA_PROGRESS::${JSON.stringify(makeProgress(stage, status))}\n`);
}

function probeCDPPort(port, timeoutMs = 400) {
  return new Promise(resolve => {
    const request = http.get(`http://127.0.0.1:${port}/json/version`, response => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    request.setTimeout(timeoutMs, () => request.destroy());
    request.on('error', () => resolve(false));
  });
}

async function waitUntil(check, timeoutMs, intervalMs = 150) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const value = await check();
    if (value) return value;
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
  return null;
}

function discoverPorts() {
  const candidates = [];
  if (process.env.ADSPOWER_CDP_PORT) {
    candidates.push({ port: Number(process.env.ADSPOWER_CDP_PORT), source: 'env', mtime: Date.now() });
  }
  const roots = ['E:\\.ADSPOWER_GLOBAL\\cache', 'C:\\.ADSPOWER_GLOBAL\\cache'];
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const marker = path.join(root, entry.name, 'DevToolsActivePort');
      if (!fs.existsSync(marker)) continue;
      try {
        const port = Number(fs.readFileSync(marker, 'utf8').split(/\r?\n/)[0].trim());
        if (Number.isInteger(port) && port > 0) {
          candidates.push({ port, source: marker, mtime: fs.statSync(marker).mtimeMs });
        }
      } catch { /* ignore stale marker */ }
    }
  }
  return prioritizeCandidates(candidates);
}

async function connectAdsPower(chromium) {
  const errors = [];
  const candidates = discoverPorts();
  emitProgress('ads_power', `probing ${candidates.length} CDP candidates`);
  const probeResults = await Promise.all(candidates.map(async candidate => ({
    candidate,
    alive: await probeCDPPort(candidate.port),
  })));
  for (const { candidate } of probeResults.filter(result => result.alive)) {
    try {
      const browser = await chromium.connectOverCDP(`http://127.0.0.1:${candidate.port}`, { timeout: 2500 });
      const pages = browser.contexts().flatMap(context => context.pages());
      const relevant = pages.some(page => /admin\.shopify\.com|uppromote\.com/.test(page.url()));
      if (relevant) {
        emitProgress('ads_power', `connected port ${candidate.port}`);
        return { browser, port: candidate.port };
      }
      errors.push(`${candidate.port}: connected but Shopify/UpPromote tab not found`);
    } catch (error) {
      errors.push(`${candidate.port}: ${error.message}`);
    }
  }
  throw new Error(`未找到已登录 Shopify/UpPromote 的 AdsPower 浏览器。${errors.join(' | ')}`);
}

function scopes(page) {
  return page.frames();
}

async function firstVisible(locators) {
  for (const locator of locators) {
    const count = await locator.count().catch(() => 0);
    for (let i = 0; i < count; i += 1) {
      const item = locator.nth(i);
      if (await item.isVisible().catch(() => false)) return item;
    }
  }
  return null;
}

async function clickText(page, text, options = {}) {
  const exact = options.exact ?? true;
  const candidates = scopes(page).flatMap(frame => [
    frame.getByRole('button', { name: text, exact }),
    frame.getByRole('link', { name: text, exact }),
    frame.getByText(text, { exact }),
  ]);
  const locator = await waitUntil(() => firstVisible(candidates), options.waitFor ?? CLICK_RESPONSE_TIMEOUT_MS, 100);
  if (!locator) throw new Error(`找不到可点击文本：${text}`);
  await locator.click({ timeout: options.timeout ?? 15000 });
  return locator;
}

// Shopify's chrome may localize global action buttons while the embedded
// UpPromote form remains English. Keep these actions bilingual so a resumed
// workflow does not mistake a visible Chinese Save/Discard control for a
// failed submission and create a duplicate affiliate.
async function clickGlobalAction(page, action, options = {}) {
  const labels = action === 'save' ? /^(Save|保存)$/ : /^(Discard|放弃)$/;
  return clickText(page, labels, { ...options, exact: true });
}

async function hasUnsavedChanges(page) {
  return firstVisible(scopes(page).flatMap(frame => [
    frame.getByText('Unsaved changes', { exact: true }),
    frame.getByText('未保存的更改', { exact: true }),
  ]));
}

async function fillField(page, label, value) {
  const candidates = scopes(page).flatMap(frame => [
    frame.getByLabel(label, { exact: false }),
    frame.getByPlaceholder(new RegExp(label, 'i')),
    frame.locator(`input[name="${label}"]`),
  ]);
  const locator = await waitUntil(() => firstVisible(candidates), CLICK_RESPONSE_TIMEOUT_MS, 100);
  if (!locator) throw new Error(`找不到输入框：${label}`);
  await locator.fill(value);
  return locator;
}

async function visibleInput(page, selector) {
  return firstVisible(scopes(page).map(frame => frame.locator(selector)));
}

async function visibleByCleanText(page, selector, text) {
  for (const frame of scopes(page)) {
    const items = frame.locator(selector);
    for (let index = 0; index < await items.count().catch(() => 0); index += 1) {
      const item = items.nth(index);
      if (await item.isVisible().catch(() => false) && cleanText(await item.innerText()) === cleanText(text)) return item;
    }
  }
  return null;
}

async function affiliateAppFrame(page) {
  for (const frame of scopes(page)) {
    const hasSearch = Boolean(await firstVisible([frame.locator('input[placeholder="Search"]:not([readonly]), input[type="search"]:not([readonly])')]));
    const hasAdd = Boolean(await firstVisible([frame.getByText('Add affiliate', { exact: true })]));
    if (frame === page.mainFrame() && !hasAdd) continue;
    if (hasSearch || hasAdd) return frame;
  }
  return null;
}

async function waitForAffiliateApp(page, timeoutMs) {
  const frame = await waitUntil(() => affiliateAppFrame(page), timeoutMs, 200);
  if (frame) return frame;
  throw new Error('UpPromote Affiliate 应用在等待时间内未加载完成');
}

async function searchAffiliate(page, email) {
  const frame = await waitUntil(async () => {
    for (const candidate of scopes(page)) {
      const input = await firstVisible([
        candidate.locator('input[placeholder="Search"]:not([readonly])'),
        candidate.locator('input[type="search"]:not([readonly])'),
      ]);
      const hasAdd = Boolean(await firstVisible([candidate.getByText('Add affiliate', { exact: true })]));
      if (shouldSearchAffiliateScope(candidate === page.mainFrame(), Boolean(input), hasAdd) && input) return candidate;
    }
    return null;
  }, 12000, 150);
  if (!frame) return false;
  const search = await firstVisible([
    frame.locator('input[placeholder="Search"]:not([readonly])'),
    frame.locator('input[type="search"]:not([readonly])'),
  ]);
  if (!search) return false;
  await search.fill(email);
  await search.press('Enter');
  const result = await waitUntil(async () => {
    // Search chips echo the query text before the table finishes refreshing.
    // Only a real table row containing the target email proves the affiliate exists.
    for (const candidate of scopes(page)) {
      const rows = candidate.locator('tbody tr');
      for (let index = 0; index < await rows.count().catch(() => 0); index += 1) {
        const rowText = cleanText(await rows.nth(index).innerText().catch(() => ''));
        if (affiliateRowMatches(rowText, email)) return true;
      }
    }
    const body = cleanText((await Promise.all(scopes(page).map(candidate => candidate.locator('body').innerText().catch(() => '')))).join(' '));
    if (body.includes('total 0 entries') || body.includes('no data')) return 'not_found';
    return null;
  }, 12000, 150);
  return result === true;
}

async function selectDropdownValue(page, currentOrLabel, searchText, finalText) {
  let trigger = await waitUntil(() => firstVisible(scopes(page).flatMap(frame => [
    frame.getByText(currentOrLabel, { exact: true }),
    frame.getByLabel(currentOrLabel, { exact: false }),
  ])), 5000, 100);
  if (!trigger) throw new Error(`找不到下拉菜单：${currentOrLabel}`);
  await trigger.click();
  if (searchText) {
    const search = await waitUntil(() => firstVisible([
      ...scopes(page).map(frame => frame.locator('.ant-select-dropdown:visible input')),
      ...scopes(page).map(frame => frame.locator('[role="listbox"] input')),
      ...scopes(page).map(frame => frame.getByPlaceholder('Search', { exact: true })),
    ]), 3000, 100);
    if (search) await search.fill(searchText);
  }
  const option = await waitUntil(() => firstVisible(scopes(page).flatMap(frame => [
    frame.locator(`.ant-select-item-option[title="${finalText}"]`),
    frame.getByText(finalText, { exact: true }),
  ])), 3000, 100);
  if (!option) throw new Error(`找不到下拉选项：${finalText}`);
  await option.click();
  const openDropdown = await firstVisible(scopes(page).map(frame => frame.locator('.ant-select-dropdown:visible')));
  if (openDropdown) {
    const selected = await visibleByCleanText(page, '.ant-select-selection-item', finalText);
    if (selected) await selected.click();
  }
}

async function ensureAffiliate(page, data) {
  let resumeCreateForm = page.url().includes('/affiliates/create');
  if (resumeCreateForm) {
    await waitForAffiliateApp(page, data.timeoutMs);
    const existingEmail = await visibleInput(page, 'input[placeholder*="email" i]');
    const currentEmail = cleanText(existingEmail ? await existingEmail.inputValue() : '');
    if (currentEmail && currentEmail !== cleanText(data.creator.email)) {
      emitProgress('affiliate', `discarding stale create form for ${currentEmail}`);
      await clickGlobalAction(page, 'discard').catch(() => {});
      await waitUntil(() => !page.url().includes('/affiliates/create'), 5000, 150);
      if (page.url().includes('/affiliates/create')) {
        await page.goto(data.adminUrl, { waitUntil: 'domcontentloaded', timeout: data.timeoutMs });
      }
      return ensureAffiliate(page, data);
    }
    const duplicateEmail = await firstVisible(scopes(page).map(frame => frame.getByText('The email has already been taken.', { exact: true })));
    if (duplicateEmail) {
      emitProgress('affiliate', 'discarding duplicate form and locating saved affiliate');
      await clickGlobalAction(page, 'discard');
      await waitUntil(() => !page.url().includes('/affiliates/create'), 5000, 150);
      if (page.url().includes('/affiliates/create')) {
        await page.goto(data.adminUrl, { waitUntil: 'domcontentloaded', timeout: data.timeoutMs });
      }
      await waitForAffiliateApp(page, data.timeoutMs);
      if (!(await searchAffiliate(page, data.creator.email))) throw new Error('邮箱已占用，但 Affiliate 列表找不到该邮箱');
      emitProgress('affiliate', 'saved affiliate recovered by exact email');
      data.firstRowOnly = false;
      return true;
    }
    emitProgress('affiliate', 'resuming matching unsaved create form');
  } else {
    emitProgress('affiliate', 'refreshing initial affiliate list for new task');
    await page.goto(data.adminUrl, { waitUntil: 'domcontentloaded', timeout: data.timeoutMs });
    await waitForAffiliateApp(page, data.timeoutMs);
    if ((!data.firstRowOnly || data.checkExistingBeforeCreate) && await searchAffiliate(page, data.creator.email)) {
      emitProgress('affiliate', 'existing affiliate found');
      data.firstRowOnly = false;
      return true;
    }
    await clickText(page, 'Add affiliate', { exact: false });
    await waitUntil(() => visibleInput(page, 'input[placeholder*="first name" i]'), 5000, 120);
  }

  const programSelected = await visibleByCleanText(page, '.ant-select-selection-item', 'KOL - $100');
  const openDropdown = await firstVisible(scopes(page).map(frame => frame.locator('.ant-select-dropdown:visible')));
  if (openDropdown) await page.keyboard.press('Escape').catch(() => {});
  if (!programSelected) await selectDropdownValue(page, 'Refer a Friend (default)', 'KOL', 'KOL - $100');
  await fillField(page, 'First name', data.creator.firstName);
  await fillField(page, 'Last name', data.creator.lastName);
  await fillField(page, 'Email', data.creator.email);
  const defaultPassword = await visibleByCleanText(page, '.ant-select-selection-item', 'Set default password');
  if (defaultPassword) {
    await defaultPassword.locator('xpath=..').click();
    const autoPassword = await waitUntil(
      () => visibleByCleanText(page, '.ant-select-item-option', 'Auto generated password'),
      CLICK_RESPONSE_TIMEOUT_MS,
      100,
    );
    if (!autoPassword) throw new Error('找不到 Auto generated password 选项');
    await autoPassword.click();
    const selectedAuto = await waitUntil(
      () => visibleByCleanText(page, '.ant-select-selection-item', 'Auto generated password'),
      CLICK_RESPONSE_TIMEOUT_MS,
      100,
    );
    if (!selectedAuto) throw new Error('Auto generated password selection was not applied');
  }
  await clickGlobalAction(page, 'save', { timeout: 30000 });
  emitProgress('affiliate', 'saved; verifying exact email');
  await waitUntil(async () => {
    if (!page.url().includes('/affiliates/create')) return true;
    const unsaved = await hasUnsavedChanges(page);
    return unsaved ? null : true;
  }, 20000, 200);
  if (page.url().includes('/affiliates/create')) {
    const unsaved = await hasUnsavedChanges(page);
    if (unsaved) {
      const duplicateEmail = await firstVisible(scopes(page).map(frame => frame.getByText('The email has already been taken.', { exact: true })));
      if (!duplicateEmail) throw new Error('Affiliate Save 在 20 秒内未完成，已停止以避免重复创建');
      emitProgress('affiliate', 'duplicate email confirmed; discarding duplicate form');
      await clickGlobalAction(page, 'discard');
      await waitUntil(() => !page.url().includes('/affiliates/create'), 5000, 150);
    }
  }
  if (page.url().includes('/affiliates/create')) {
    await page.goto(data.adminUrl, { waitUntil: 'domcontentloaded', timeout: data.timeoutMs });
  }
  await waitForAffiliateApp(page, data.timeoutMs);
  if (data.firstRowOnly) {
    const firstRow = await waitUntil(() => firstAffiliateRow(page), CLICK_RESPONSE_TIMEOUT_MS, 120);
    if (!firstRow || !firstRowMatchesTarget(await firstRow.innerText().catch(() => ''), data.creator.email)) {
      throw new Error('Saved affiliate is not the first visible row');
    }
    return false;
  }
  if (!(await searchAffiliate(page, data.creator.email))) throw new Error('Affiliate 保存后未能重新搜索到');
  return false;
}

async function openAffiliateRowAction(page, email, actionText, firstRowOnly = false) {
  if (firstRowOnly) {
    const row = await waitUntil(() => firstAffiliateRow(page), CLICK_RESPONSE_TIMEOUT_MS, 120);
    if (!row || !firstRowMatchesTarget(await row.innerText().catch(() => ''), email)) {
      throw new Error(`First affiliate row does not match ${email}`);
    }
    const action = await firstVisible([
      row.getByText(actionText, { exact: true }),
      row.getByRole('button', { name: actionText, exact: true }),
      row.getByRole('link', { name: actionText, exact: true }),
    ]);
    if (!action) throw new Error(`First affiliate row is missing ${actionText}`);
    await action.click();
    return;
  }
  for (const frame of scopes(page)) {
    const rows = frame.locator('tbody tr');
    for (let index = 0; index < await rows.count().catch(() => 0); index += 1) {
      const row = rows.nth(index);
      const rowText = cleanText(await row.innerText().catch(() => ''));
      if (!affiliateRowMatches(rowText, email)) continue;
      const action = await firstVisible([
        row.getByText(actionText, { exact: true }),
        row.getByRole('button', { name: actionText, exact: true }),
        row.getByRole('link', { name: actionText, exact: true }),
      ]);
      if (action) { await action.click(); return; }
    }
  }
  const emailNode = await firstVisible(scopes(page).map(frame => frame.getByText(email, { exact: false })));
  if (!emailNode) throw new Error(`列表中找不到 Affiliate：${email}`);
  const containers = [emailNode.locator('xpath=ancestor::tr[1]'), emailNode.locator('xpath=ancestor::*[self::div or self::li][.//button or .//a][1]')];
  for (const container of containers) {
    if (!(await container.count().catch(() => 0))) continue;
    const action = await firstVisible([
      container.getByRole('button', { name: actionText, exact: false }),
      container.getByRole('link', { name: actionText, exact: false }),
      container.getByText(actionText, { exact: false }),
    ]);
    if (action) { await action.click(); return; }
  }
  throw new Error(`找不到 ${actionText} 操作`);
}

async function ensureCoupon(page, data, resumeForm = false) {
  emitProgress('coupon', 'opening coupon management');
  if (!resumeForm) {
    await openAffiliateRowAction(page, data.creator.email, 'Manage', data.firstRowOnly);
    const assignedTab = await waitUntil(
      () => firstVisible(scopes(page).map(frame => frame.getByText('View assigned coupons', { exact: true }))),
      CLICK_RESPONSE_TIMEOUT_MS,
    );
    if (assignedTab) {
      await assignedTab.click();
      const initialText = (await Promise.all(scopes(page).map(frame => frame.locator('body').innerText().catch(() => '')))).join(' ');
      if (assignedCouponsAction(initialText, data.creator.code) !== 'add') {
        const existing = await waitUntil(
          () => firstVisible(scopes(page).map(frame => frame.getByText(data.creator.code, { exact: true }))),
          CLICK_RESPONSE_TIMEOUT_MS,
          120,
        );
        if (existing) {
          const pageText = cleanText((await Promise.all(scopes(page).map(frame => frame.locator('body').innerText().catch(() => '')))).join(' '));
          if (!pageText.includes('100')) throw new Error('同名优惠码已存在，但无法 verify $100 amount');
          emitProgress('coupon', 'existing coupon verified');
          return;
        }
      }
    }
    const addTab = await waitUntil(
      () => firstVisible(scopes(page).map(frame => frame.getByText('Add coupon', { exact: true }))),
      CLICK_RESPONSE_TIMEOUT_MS,
    );
    if (!addTab) throw new Error('Manage coupons page is missing Add coupon');
    await addTab.click();
  } else if (false) {
    emitProgress('coupon', 'resuming current matching coupon form');
    // A successful save resets the Add coupon form to blank while leaving the
    // same URL open. Check Assigned first so a resume never creates a duplicate.
    const assignedTab = await firstVisible(scopes(page).map(frame => frame.getByText('View assigned coupons', { exact: true })));
    if (assignedTab) {
      await assignedTab.click();
      const initialText = (await Promise.all(scopes(page).map(frame => frame.locator('body').innerText().catch(() => '')))).join(' ');
      if (assignedCouponsAction(initialText, data.creator.code) === 'add') {
        emitProgress('coupon', 'no assigned coupons; opening Add coupon immediately');
        await clickText(page, 'Add coupon', { exact: true });
      } else {
      const existing = await waitUntil(
        () => firstVisible(scopes(page).map(frame => frame.getByText(data.creator.code, { exact: true }))),
        CLICK_RESPONSE_TIMEOUT_MS,
        120,
      );
      if (existing) {
        emitProgress('coupon', 'existing coupon verified after save');
        return;
      }
      await clickText(page, 'Add coupon', { exact: true });
      }
    }
  }
  const codeInput = await waitUntil(() => visibleInput(page, 'input[placeholder="Enter coupon code"]'), 5000, 120);
  if (!codeInput) throw new Error('找不到 Coupon code 输入框');
  await codeInput.fill(data.creator.code);
  if (!(await firstVisible(scopes(page).map(frame => frame.locator('.ant-select-selection-item[title="Product discount"]'))))) {
    await selectDropdownValue(page, 'Discount type', null, 'Product discount');
  }
  if (!(await firstVisible(scopes(page).map(frame => frame.locator('.ant-select-selection-item[title="Fixed amount"]'))))) {
    await selectDropdownValue(page, 'Value type', null, 'Fixed amount');
  }
  const amount = await visibleInput(page, 'input[type="number"][placeholder="0.00"]');
  if (!amount) throw new Error('找不到 Amount 输入框');
  await amount.fill('100');
  const appliesCurrent = await firstVisible(scopes(page).flatMap(frame => [
    frame.locator('.ant-select-selection-item[title="All products"]'),
    frame.locator('.ant-select-selection-item[title="Specific products"]'),
    frame.locator('.ant-select-selection-item[title="Specific collections"]'),
  ]));
  if (!appliesCurrent) throw new Error('找不到 Applies to 当前值');
  if (cleanText(await appliesCurrent.innerText()) !== 'specific collections') {
    const appliesSelector = appliesCurrent.locator('xpath=ancestor::div[contains(@class,"ant-select-selector")][1]');
    await (await appliesSelector.count() ? appliesSelector : appliesCurrent).click();
    const option = await waitUntil(async () => {
      for (const frame of scopes(page)) {
        const candidate = frame.locator('.ant-select-item-option[title="Specific collections"]');
        if (await candidate.count().catch(() => 0)) return candidate.first();
      }
      return null;
    }, CLICK_RESPONSE_TIMEOUT_MS, 100);
    if (!option) throw new Error('找不到 Specific collections 选项');
    await option.evaluate(node => node.click());
  }
  const alreadySelected = await visibleByCleanText(page, '.ant-select-selection-item, .ant-select-selection-item-content', 'Electric Dirt Bike');
  if (!alreadySelected) {
    const collectionTrigger = await waitUntil(() => firstVisible(scopes(page).flatMap(frame => [
      frame.locator('input[placeholder="Search and select collections here"]'),
      frame.getByText('Search and select collections here', { exact: true }),
    ])), CLICK_RESPONSE_TIMEOUT_MS, 120);
    if (!collectionTrigger) throw new Error('找不到 Select collections');
    const selector = collectionTrigger.locator('xpath=ancestor::div[contains(@class,"ant-select-selector")][1]');
    await (await selector.count() ? selector : collectionTrigger).click();
    const collectionSearch = await waitUntil(async () => {
      for (const frame of scopes(page)) {
        const candidate = frame.locator('input[placeholder="Type and search here"]');
        if (await candidate.count().catch(() => 0)) return candidate.first();
      }
      return null;
    }, CLICK_RESPONSE_TIMEOUT_MS, 100);
    if (!collectionSearch) throw new Error('找不到 collection 搜索框');
    await collectionSearch.fill('Electric Dirt Bike', { force: true });
    const exactCollection = await waitUntil(async () => {
      for (const frame of scopes(page)) {
        const options = frame.locator('.ant-select-item-option');
        for (let index = 0; index < await options.count(); index += 1) {
          const option = options.nth(index);
          if (isExactCollectionCandidate(await option.innerText(), 'Electric Dirt Bike')) return option;
        }
      }
      return null;
    }, CLICK_RESPONSE_TIMEOUT_MS, 120);
    if (!exactCollection) throw new Error('找不到精确的 Electric Dirt Bike collection');
    await exactCollection.evaluate(node => node.click());
  }
  for (const name of ['Product discounts', 'Order discounts', 'Free shipping discounts']) {
    const checkbox = await firstVisible(scopes(page).flatMap(frame => [
      ...combinationCheckboxSelectors(name).map(selector => frame.locator(selector)),
      frame.getByLabel(name, { exact: true }),
    ]));
    if (!checkbox) throw new Error(`Combination checkbox not found: ${name}`);
    if (!(await checkbox.isChecked().catch(() => false))) await checkbox.check({ force: true });
    if (!(await checkbox.isChecked().catch(() => false))) throw new Error(`Combination checkbox was not selected: ${name}`);
  }
  await clickGlobalAction(page, 'save', { timeout: 30000 });
  let verified = await waitUntil(async () => {
    const bodyText = (await Promise.all(
      scopes(page).map(frame => frame.locator('body').innerText().catch(() => '')),
    )).join(' ');
    return couponSaveVerified(bodyText, data.creator.code) ? true : null;
  }, CLICK_RESPONSE_TIMEOUT_MS, 150);
  if (!verified) {
    const assignedTab = await firstVisible(scopes(page).map(frame => frame.getByText('View assigned coupons', { exact: true })));
    if (assignedTab) {
      emitProgress('coupon', 'save result ambiguous; checking assigned coupon once');
      await assignedTab.click();
      verified = await waitUntil(async () => {
        const bodyText = (await Promise.all(
          scopes(page).map(frame => frame.locator('body').innerText().catch(() => '')),
        )).join(' ');
        return cleanText(bodyText).includes(cleanText(data.creator.code)) ? true : null;
      }, CLICK_RESPONSE_TIMEOUT_MS, 150);
    }
  }
  if (!verified) throw new Error('Coupon 保存后未能验证 code');
  emitProgress('coupon', 'coupon saved and verified');
}

async function tryOpenAffiliateDetailInline(page, data) {
  const currentBody = (await Promise.all(
    scopes(page).map(frame => frame.locator('body').innerText().catch(() => '')),
  )).join(' ');
  if (chooseDetailNavigation({ url: page.url(), bodyText: currentBody, targetEmail: data.creator.email }) !== 'inline') {
    return false;
  }
  for (const frame of scopes(page)) {
    const emailNode = await firstVisible([frame.getByText(data.creator.email, { exact: false })]);
    if (!emailNode) continue;
    const card = emailNode.locator('xpath=ancestor::div[.//*[normalize-space()="Affiliate"]][1]');
    const nameNode = await firstVisible([
      card.getByText(data.creator.name, { exact: false }),
      frame.getByText(data.creator.name, { exact: false }),
    ]);
    if (!nameNode) continue;
    const link = nameNode.locator('xpath=ancestor::a[1]');
    await (await link.count() ? link : nameNode).click().catch(() => {});
    const opened = await waitUntil(async () => {
      const emailReady = (await Promise.all(
        scopes(page).map(scope => scope.locator('body').innerText().catch(() => '')),
      )).some(body => cleanText(body).includes(cleanText(data.creator.email)));
      const customPath = await visibleInput(page, 'input[placeholder*="custom path" i]');
      return emailReady && customPath;
    }, CLICK_RESPONSE_TIMEOUT_MS, 120);
    if (opened) return true;
  }
  return false;
}

async function openAffiliateDetail(page, data, resumeCurrent = false) {
  emitProgress('affiliate_link', 'opening affiliate detail');
  if (!resumeCurrent) {
    const openedInline = data.firstRowOnly ? false : await tryOpenAffiliateDetailInline(page, data);
    if (openedInline) emitProgress('affiliate_link', 'opened inline from coupon page');
    if (!openedInline) {
    await page.goto(data.adminUrl, { waitUntil: 'domcontentloaded', timeout: data.timeoutMs });
    await waitForAffiliateApp(page, data.timeoutMs);
    if (data.firstRowOnly) {
      const firstRow = await waitUntil(() => firstAffiliateRow(page), CLICK_RESPONSE_TIMEOUT_MS, 120);
      if (!firstRow || !firstRowMatchesTarget(await firstRow.innerText().catch(() => ''), data.creator.email)) {
        throw new Error('First affiliate row does not match the current creator');
      }
      const firstName = await firstVisible([firstRow.getByText(data.creator.name, { exact: false })]);
      if (!firstName) throw new Error(`First affiliate row is missing creator name: ${data.creator.name}`);
      await firstName.click();
    } else {
    if (!(await searchAffiliate(page, data.creator.email))) throw new Error('无法重新定位 Affiliate');
    let nameNode = null;
    for (const frame of scopes(page)) {
      const rows = frame.locator('tbody tr');
      for (let index = 0; index < await rows.count().catch(() => 0); index += 1) {
        const row = rows.nth(index);
        if (!affiliateRowMatches(await row.innerText().catch(() => ''), data.creator.email)) continue;
        nameNode = await firstVisible([row.getByText(data.creator.name, { exact: false })]);
        if (!nameNode) {
          nameNode = await firstVisible([
            row.locator('span[class*="affiliateName"]').first(),
            row.locator('a').first(),
            row.locator('td').nth(1),
          ]);
        }
        if (nameNode) break;
      }
      if (nameNode) break;
    }
    if (!nameNode) throw new Error(`找不到 Affiliate 姓名：${data.creator.name}`);
    await nameNode.click();
    }
    }
  } else {
    emitProgress('affiliate_link', 'resuming current matching detail page');
  }
  const detailReady = await waitUntil(async () => {
    const bodies = await Promise.all(scopes(page).map(frame => frame.locator('body').innerText().catch(() => '')));
    return bodies.some(body => cleanText(body).includes(cleanText(data.creator.email)));
  }, CLICK_RESPONSE_TIMEOUT_MS, 150);
  if (!detailReady) throw new Error('Affiliate 详情数据在 7 秒内未加载完成');
  const customPath = await waitUntil(() => visibleInput(page, 'input[placeholder*="custom path" i]'), CLICK_RESPONSE_TIMEOUT_MS, 120);
  if (!customPath) throw new Error('找不到 custom affiliate link 输入框');
  if ((await customPath.inputValue()) !== data.creator.code) {
    await customPath.fill(data.creator.code);
    await clickGlobalAction(page, 'save', { timeout: 30000 });
    const saved = await waitUntil(async () => {
      const unsaved = await hasUnsavedChanges(page);
      return !unsaved && (await customPath.inputValue()) === data.creator.code;
    }, CLICK_RESPONSE_TIMEOUT_MS, 120);
    if (!saved) throw new Error('Custom affiliate link 保存验证失败');
  }
  emitProgress('affiliate_link', 'custom path verified');
}

async function loginAffiliate(page, data) {
  const context = page.context();
  const pagesBefore = new Set(context.pages());
  const popupPromise = context.waitForEvent('page', { timeout: 10000 }).catch(() => null);
  const loginText = await firstVisible(scopes(page).map(frame => frame.getByText('Login as affiliate', { exact: true })));
  if (!loginText) throw new Error('找不到 Login as affiliate');
  const loginButton = loginText.locator('xpath=ancestor::button[1]');
  await (await loginButton.count() ? loginButton : loginText).click();
  const popup = await popupPromise;
  const newPages = context.pages().filter(candidate => !pagesBefore.has(candidate));
  const candidates = [popup, ...newPages, ...context.pages().slice().reverse()].filter(Boolean);
  const dashboard = await waitUntil(async () => {
    for (const candidate of candidates) {
      if (!/uppromote\.com/.test(candidate.url())) continue;
      const body = (await Promise.all(scopes(candidate).map(frame => frame.locator('body').innerText().catch(() => '')))).join(' ');
      const productLink = await firstVisible(scopes(candidate).map(frame => frame.getByText('Get product link', { exact: true })));
      if (affiliateDashboardReady(body, Boolean(productLink), data.creator.name, data.creator.code)) return candidate;
    }
    return null;
  }, 20000, 200) || popup || page;
  await dashboard.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => {});
  emitProgress('affiliate_login', 'affiliate dashboard ready');
  return dashboard;
}

async function generateShortLink(page, data, modalAlreadyOpen = false) {
  emitProgress('short_link', 'opening product link generator');
  if (!modalAlreadyOpen) await clickText(page, 'Get product link', { exact: true });
  const modal = await waitUntil(() => firstVisible(scopes(page).map(frame => frame.locator('#productLinkModal'))), CLICK_RESPONSE_TIMEOUT_MS, 100);
  if (!modal) throw new Error('Get product link modal 未打开');
  shortLinkEntryAction(extractShortLink(await modal.locator('table tbody').innerText().catch(() => '')));
  const destinationInput = await firstVisible([
    modal.locator('input[placeholder="Enter a product/collection/page link here"]'),
    modal.locator('input[placeholder*="link here" i]'),
  ]);
  if (!destinationInput) throw new Error('Get product link 中找不到 Link here 输入框');
  await destinationInput.fill(data.destination);
  const generateButton = await firstVisible([
    modal.locator('button').filter({ hasText: 'Generate' }).first(),
    modal.getByText('Generate', { exact: true }),
  ]);
  if (!generateButton) throw new Error('找不到 Generate');
  await generateButton.click();
  const output = modal.locator('input[placeholder="Your link will appear here"]');
  const fullLink = await waitUntil(async () => {
    const value = await output.inputValue().catch(() => '');
    return isGeneratedAffiliateLink(value, data.destination) ? value : null;
  }, CLICK_RESPONSE_TIMEOUT_MS, 120);
  if (!fullLink) throw new Error('Generate 后未生成 affiliate link');
  const shortenButton = await firstVisible([
    modal.locator('button').filter({ hasText: 'Get shortened link' }).first(),
    modal.getByText('Get shortened link', { exact: true }),
  ]);
  if (!shortenButton) throw new Error('找不到 Get shortened link');
  await shortenButton.click();
  const shortLink = await waitUntil(async () => {
    const value = await output.inputValue().catch(() => '');
    return /https:\/\/(?:bit\.ly|tinyurl\.com|t\.co)\/[A-Za-z0-9_-]+/.test(value) ? value : null;
  }, CLICK_RESPONSE_TIMEOUT_MS, 150);
  if (!isValidShortLink(shortLink)) throw new Error('没有生成有效短链接');
  const saveButton = await firstVisible([
    modal.getByText('Copy & save', { exact: true }),
    modal.locator('button.btn-primary.hidden-xs').first(),
  ]);
  if (!saveButton) throw new Error('找不到 Copy & save');
  await saveButton.click();
  const saved = await waitUntil(async () => {
    const tableText = await modal.locator('table tbody').innerText().catch(() => '');
    return tableText.includes(shortLink);
  }, CLICK_RESPONSE_TIMEOUT_MS, 150);
  if (!saved) throw new Error('短链接未出现在 Saved link 表格');
  emitProgress('short_link', 'short link saved and verified');
  return shortLink;
}

async function workflowSnapshot(page, data) {
  const bodies = await Promise.all(scopes(page).map(frame => frame.locator('body').innerText().catch(() => '')));
  const modal = await firstVisible(scopes(page).map(frame => frame.locator('#productLinkModal')));
  return classifyWorkflowSnapshot({
    url: page.url(),
    bodyText: bodies.join(' '),
    hasProductLinkModal: Boolean(modal),
    targetEmail: data.creator.email,
    targetCode: data.creator.code,
  });
}

async function closeAffiliateDashboardPage(page) {
  if (!page || page.isClosed()) return;
  if (!/admin\.shopify\.com/i.test(page.url())) {
    await page.close().catch(() => {});
    emitProgress('cleanup', 'closed completed affiliate dashboard tab');
  }
}

async function resetFailedTaskPage(page, context, adminUrl) {
  if (!page || page.isClosed()) return;
  if (!/admin\.shopify\.com/i.test(page.url())) {
    await page.close().catch(() => {});
    emitProgress('cleanup', 'closed failed affiliate dashboard tab');
    return;
  }
  await page.close({ runBeforeUnload: false }).catch(() => {});
  const replacement = await context.newPage().catch(() => null);
  if (replacement) {
    await replacement.goto(adminUrl, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});
  }
  emitProgress('cleanup', 'closed failed creator page and reopened affiliate list');
}

async function run(data) {
  const { chromium } = require('playwright');
  const { browser } = await connectAdsPower(chromium);
  const context = browser.contexts()[0];
  let page = context.pages().find(p => /admin\.shopify\.com/.test(p.url())) || context.pages()[0] || await context.newPage();
  try {
    if (regenerateLinkPlan(data.regenerateLinkOnly)) {
      emitProgress('resume', 'regenerating link for existing affiliate');
      emitProgress('affiliate', 'refreshing initial affiliate list for new task');
      await page.goto(data.adminUrl, { waitUntil: 'domcontentloaded', timeout: data.timeoutMs });
      await waitForAffiliateApp(page, data.timeoutMs);
      const affiliateExisted = await searchAffiliate(page, data.creator.email);
      if (regenerateAffiliateAction(affiliateExisted) === 'stop') {
        throw new Error('Existing affiliate not found; regenerate-link mode will not create a duplicate');
      }
      await openAffiliateDetail(page, data);
      page = await loginAffiliate(page, data);
      const shortLink = await generateShortLink(page, data);
      await closeAffiliateDashboardPage(page);
      return makeResult(shortLink, true, true);
    }
    let stage = 'affiliate_list';
    for (const candidate of context.pages().slice().reverse()) {
      const candidateStage = await workflowSnapshot(candidate, data);
      if (candidateStage !== 'affiliate_list') {
        page = candidate;
        stage = candidateStage;
        break;
      }
    }
    emitProgress('resume', `detected ${stage}`);
    let affiliateExisted = true;
    let shortLink;
    if (stage === 'short_link_modal') {
      shortLink = await generateShortLink(page, data, true);
    } else if (stage === 'affiliate_dashboard') {
      shortLink = await generateShortLink(page, data, false);
    } else {
      if (stage === 'affiliate_list' || stage === 'affiliate_create') {
        affiliateExisted = await ensureAffiliate(page, data);
        await ensureCoupon(page, data);
        await openAffiliateDetail(page, data);
      } else if (stage === 'coupon_form') {
        await ensureCoupon(page, data, true);
        await openAffiliateDetail(page, data);
      } else if (stage === 'affiliate_detail') {
        await openAffiliateDetail(page, data, true);
      }
      page = await loginAffiliate(page, data);
      shortLink = await generateShortLink(page, data);
    }
    await closeAffiliateDashboardPage(page);
    return makeResult(shortLink, affiliateExisted, true);
  } catch (error) {
    const shot = path.join(__dirname, 'logs', `uppromote-error-${Date.now()}.png`);
    fs.mkdirSync(path.dirname(shot), { recursive: true });
    await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
    await resetFailedTaskPage(page, context, data.adminUrl);
    throw new Error(`${error.message}；截图：${shot}`);
  }
}

module.exports = {
  cleanText,
  isValidShortLink,
  makeResult,
  uniqueBy,
  discoverPorts,
  isAppReadySnapshot,
  prioritizeCandidates,
  isExactCollectionCandidate,
  makeProgress,
  probeCDPPort,
  connectAdsPower,
  affiliateAppFrame,
  classifyWorkflowSnapshot,
  isGeneratedAffiliateLink,
  CLICK_RESPONSE_TIMEOUT_MS,
  workflowSnapshot,
  extractShortLink,
  shortLinkEntryAction,
  regenerateLinkPlan,
  shouldSearchAffiliateScope,
  regenerateAffiliateAction,
  affiliateDashboardReady,
  firstRowMatchesTarget,
  affiliateRowMatches,
  chooseDetailNavigation,
  assignedCouponsAction,
  couponPageEntryAction,
  couponSaveVerified,
  combinationCheckboxSelectors,
  isAffiliateListUrl,
  affiliateListEntryAction,
};

if (require.main === module) {
  const inputPath = process.argv[2];
  if (!inputPath) {
    process.stderr.write('Usage: node uppromote_worker.cjs input.json\n');
    process.exit(2);
  }
  const data = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  run(data)
    // The CDP connection intentionally leaves the user's AdsPower browser open.
    // Exit after flushing the result so Playwright's live socket cannot keep the
    // worker (and therefore the Python/Feishu/Gmail stages) hanging forever.
    .then(result => process.stdout.write(`VARLA_RESULT::${JSON.stringify(result)}\n`, () => process.exit(0)))
    .catch(error => process.stderr.write(`${error.stack || error.message}\n`, () => process.exit(1)));
}
