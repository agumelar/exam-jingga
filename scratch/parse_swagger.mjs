import https from 'https';

https.get('https://data.smkn1rongga.sch.id/docs/swagger-ui-init.js', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const match = data.match(/"swaggerDoc":\s*({[\s\S]*?}),\s*"customOptions"/);
    if (match) {
      try {
        const doc = JSON.parse(match[1]);
        console.log('SWAGGER PATHS:');
        console.log(JSON.stringify(Object.keys(doc.paths), null, 2));
      } catch (e) {
        console.error('Parse error:', e);
      }
    } else {
      console.log('No match found');
    }
  });
});
