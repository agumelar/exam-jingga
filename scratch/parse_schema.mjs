import https from 'https';

https.get('https://data.smkn1rongga.sch.id/docs/swagger-ui-init.js', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const match = data.match(/"swaggerDoc":\s*({[\s\S]*?}),\s*"customOptions"/);
    if (match) {
      const doc = JSON.parse(match[1]);
      console.log('STUDENTS GET:');
      console.log(JSON.stringify(doc.paths['/v1/students']?.get, null, 2));
      console.log('STAFF GET:');
      console.log(JSON.stringify(doc.paths['/v1/staff']?.get, null, 2));
    }
  });
});
