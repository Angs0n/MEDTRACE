// server: token-service.js
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

function generateAccessToken(patientRef) {
  const jti = crypto.randomUUID(); // unique ID, lets you mark it "used"
  
  const token = jwt.sign(
    { 
      ref: patientRef,   // the patient_ref pointer, NOT medical data
      jti,
      type: 'qr_access'
    },
    process.env.QR_SIGNING_SECRET, // store in KMS/secrets manager, never in code
    { expiresIn: '45s' }           // short-lived — this is what makes it "rotating"
  );

  return token;
}






// server: routes.js
app.get('/api/patient/qr-token', authenticatePatientSession, (req, res) => {
  const token = generateAccessToken(req.patient.ref);
  res.json({ 
    payload: `https://medtrace.ng/api/v1/access?token=${token}`,
    expiresIn: 45 
  });
});





// provider app, after camera scan returns the decoded string
async function handleScan(decodedUrl) {
  const res = await fetch(decodedUrl, {
    headers: { 
      Authorization: `Bearer ${providerSessionToken}` // Layer 3: provider auth
    },
  });

  if (!res.ok) {
    // generic failure message — don't leak WHY (expired vs invalid vs revoked)
    showError('Unable to access record. Code may have expired — ask patient to refresh.');
    return;
  }

  const patientData = await res.json();
  renderPatientRecord(patientData); // only shows what server decided to return
}




app.get('/api/v1/access', authenticateProvider, async (req, res) => {
  const { token } = req.query;

  let decoded;
  try {
    decoded = jwt.verify(token, process.env.QR_SIGNING_SECRET);
  } catch (err) {
    return res.status(401).json({ error: 'invalid_or_expired' });
  }

  if (await isTokenUsed(decoded.jti)) {
    return res.status(401).json({ error: 'invalid_or_expired' }); // same generic message
  }
  await markTokenUsed(decoded.jti); // single-use enforcement

  const consentResult = await resolveConsent(decoded.ref, req.provider);
  if (consentResult.status === 'denied') {
    return res.status(403).json({ error: 'access_denied' });
  }

  const data = await getPatientData(decoded.ref, consentResult.tier);
  await logAccess({ patientRef: decoded.ref, provider: req.provider, tier: consentResult.tier });

  res.json(data);
});