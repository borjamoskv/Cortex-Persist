const fs = require('fs');
const content = fs.readFileSync('cortex/scripts/doxxeo_global/DoxxGlobal.js', 'utf8');

// We leave the array intact but we process it dynamically before putting it in JSON.
// Actually, let's replace the script to dynamically clean the array!
