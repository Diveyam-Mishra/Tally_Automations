const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function fetchInvoicesForDate(targetDateStr = '01-10-2026', limit = 5) {
  const authPath = path.join(__dirname, 'auth.json');
  if (!fs.existsSync(authPath)) {
    console.error('❌ auth.json not found! Please run `node save_login.js` first.');
    process.exit(1);
  }

  // Parse DD-MM-YYYY
  const [day, month, year] = targetDateStr.split('-').map(Number);
  // IST is UTC+5:30. 
  // From date: Previous day 18:30:00.000Z
  const prevDate = new Date(Date.UTC(year, month - 1, day - 1, 18, 30, 0, 0));
  const toDate = new Date(Date.UTC(year, month - 1, day, 18, 29, 59, 999));

  const fromDateIso = prevDate.toISOString();
  const toDateIso = toDate.toISOString();

  console.log(`\n=============================================================`);
  console.log(`📦 FieldAssist DMS Invoice Fetcher`);
  console.log(`📅 Target Date : ${targetDateStr} (From: ${fromDateIso} To: ${toDateIso})`);
  console.log(`🎯 Limit       : ${limit} invoices`);
  console.log(`=============================================================\n`);

  console.log('🚀 Initializing authenticated browser context...');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({
    storageState: authPath,
    viewport: { width: 1366, height: 768 },
  });
  const page = await context.newPage();

  // Navigate to home to establish cookies & storage tokens
  console.log('🔑 Authenticating session...');
  await page.goto('https://dms-hsfpl.fieldassist.io/home');
  await page.waitForTimeout(4000);

  console.log('📡 Fetching invoice list for date...');
  const listUrl = `https://dms-hsfpl.fieldassist.io/api/v1/sales-invoices/?seller-id=19135&from-date=${encodeURIComponent(fromDateIso)}&to-date=${encodeURIComponent(toDateIso)}&beat-name=null&salesman-name=null&payment-status=null&has-sku-detail=false`;

  const listResponse = await page.evaluate(async (url) => {
    const res = await fetch(url, { headers: { 'Accept': 'application/json, text/plain, */*' } });
    return { status: res.status, data: await res.json() };
  }, listUrl);

  if (listResponse.status !== 200 || !Array.isArray(listResponse.data)) {
    console.error('❌ Failed to fetch invoice list! Status:', listResponse.status);
    await browser.close();
    return;
  }

  const allInvoices = listResponse.data;
  console.log(`✅ Found total ${allInvoices.length} invoices on ${targetDateStr}!`);

  const selectedInvoices = allInvoices.slice(0, limit);
  console.log(`⏳ Fetching full line item details for ${selectedInvoices.length} invoices...\n`);

  const invoicesDir = path.join(__dirname, 'invoices');
  if (!fs.existsSync(invoicesDir)) fs.mkdirSync(invoicesDir, { recursive: true });
  const outputFilename = `invoices_${targetDateStr}.json`;
  const outputPath = path.join(invoicesDir, outputFilename);

  // Resume capability: if file exists, load already fetched invoices
  let fullInvoices = [];
  const fetchedIds = new Set();
  if (fs.existsSync(outputPath)) {
    try {
      const existing = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
      if (Array.isArray(existing) && existing.length > 0) {
        fullInvoices = existing;
        existing.forEach(inv => {
          if (inv.id) fetchedIds.add(inv.id);
        });
        console.log(`📂 Found existing cached data: ${fetchedIds.size} invoices already downloaded.`);
      }
    } catch (e) {}
  }

  for (let i = 0; i < selectedInvoices.length; i++) {
    const header = selectedInvoices[i];
    const invoiceId = header.id;
    const invNo = header.invoiceNo;

    if (fetchedIds.has(invoiceId)) {
      console.log(`   [${i + 1}/${selectedInvoices.length}] Skipping ${invNo} (already fetched)`);
      continue;
    }

    process.stdout.write(`   [${i + 1}/${selectedInvoices.length}] Fetching ${invNo} (ID: ${invoiceId})... `);

    const detailUrl = `https://dms-hsfpl.fieldassist.io/api/v1/sales-invoices/${invoiceId}`;
    let success = false;

    for (let attempt = 1; attempt <= 3; attempt++) {
      const detailRes = await page.evaluate(async (url) => {
        try {
          const res = await fetch(url, { headers: { 'Accept': 'application/json, text/plain, */*' } });
          if (res.status === 200) {
            return { status: 200, data: await res.json() };
          }
          const text = await res.text();
          return { status: res.status, error: text };
        } catch (e) {
          return { status: 0, error: e.message };
        }
      }, detailUrl);

      if (detailRes.status === 200 && detailRes.data) {
        const invData = detailRes.data;
        const itemCount = invData.items ? invData.items.length : 0;
        console.log(`✅ OK (${itemCount} items, Total: ₹${invData.totalValueWithTcs || invData.totalValue})`);
        fullInvoices.push(invData);
        fetchedIds.add(invoiceId);
        success = true;

        // Save progress to disk incrementally every 5 invoices
        if (fullInvoices.length % 5 === 0) {
          fs.writeFileSync(outputPath, JSON.stringify(fullInvoices, null, 2), 'utf-8');
        }
        break;
      } else if (detailRes.status === 401 || detailRes.status === 403) {
        console.log(`\n      ⚠️ Session expired (HTTP ${detailRes.status}). Refreshing token via home page (attempt ${attempt}/3)...`);
        await page.goto('https://dms-hsfpl.fieldassist.io/home');
        await page.waitForTimeout(4000);
      } else {
        console.log(`\n      ⚠️ API returned status ${detailRes.status}. Retrying in 2s (attempt ${attempt}/3)...`);
        await page.waitForTimeout(2000);
      }
    }

    if (!success) {
      console.log(`❌ Failed after 3 attempts`);
    }

    // Gentle delay between requests
    await page.waitForTimeout(300);
  }

  await browser.close();

  // Save the final structured JSON into invoices/ folder
  fs.writeFileSync(outputPath, JSON.stringify(fullInvoices, null, 2), 'utf-8');

  console.log(`\n=============================================================`);
  console.log(`🎉 SUCCESS! Saved ${fullInvoices.length} invoices to:\n${outputPath}`);
  console.log(`=============================================================\n`);

  // Print a summary table
  console.log('📋 SUMMARY TABLE:');
  console.log('-'.repeat(95));
  console.log(
    'Inv No'.padEnd(16) +
    'Customer'.padEnd(30) +
    'Items'.padEnd(8) +
    'Taxable (₹)'.padStart(12) +
    'Tax (₹)'.padStart(12) +
    'Total (₹)'.padStart(14)
  );
  console.log('-'.repeat(95));

  let sumTaxable = 0;
  let sumTax = 0;
  let sumTotal = 0;

  fullInvoices.forEach(inv => {
    const no = (inv.invoiceNo || '').padEnd(16);
    const cust = (inv.buyerFirmName || '').substring(0, 28).padEnd(30);
    const count = String(inv.items ? inv.items.length : 0).padEnd(8);
    const taxable = Number(inv.netValue || inv.grossValue || 0);
    const tax = Number(inv.totalGST || inv.taxValue || 0);
    const total = Number(inv.totalValueWithTcs || inv.totalValue || 0);

    sumTaxable += taxable;
    sumTax += tax;
    sumTotal += total;

    console.log(
      no +
      cust +
      count +
      taxable.toFixed(2).padStart(12) +
      tax.toFixed(2).padStart(12) +
      total.toFixed(2).padStart(14)
    );
  });

  console.log('-'.repeat(95));
  console.log(
    'TOTAL'.padEnd(54) +
    sumTaxable.toFixed(2).padStart(12) +
    sumTax.toFixed(2).padStart(12) +
    sumTotal.toFixed(2).padStart(14)
  );
  console.log('-'.repeat(95));
}

const args = process.argv.slice(2);
const dateArg = args[0] || '01-10-2026';
const limitArg = args[1] ? parseInt(args[1], 10) : 5;

fetchInvoicesForDate(dateArg, limitArg);
