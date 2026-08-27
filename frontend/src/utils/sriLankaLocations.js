/*
  Reference gazetteer of real Sri Lankan cities/towns with their real
  lat/lon, grouped by province -- lets an operator pick a familiar place
  name instead of typing raw GPS coordinates. Selecting one just fills in
  latitude/longitude for the existing /api/disposition request (see
  Disposition.jsx); precise manual lat/lon entry stays available for
  anyone who has an exact reading.

  Same static-reference-data pattern as utils/materials.js. Coordinates
  are town-centre approximations, not survey-grade -- fine for "which
  corner of the country is this batch coming from", which is all the
  nearest-facility routing in services/facility_service.py needs.
*/

export const SRI_LANKA_LOCATIONS = [
  // Western Province
  { name: 'Colombo', province: 'Western', lat: 6.9271, lon: 79.8612 },
  { name: 'Sri Jayawardenepura Kotte', province: 'Western', lat: 6.8905, lon: 79.9018 },
  { name: 'Dehiwala-Mount Lavinia', province: 'Western', lat: 6.8410, lon: 79.8653 },
  { name: 'Moratuwa', province: 'Western', lat: 6.7730, lon: 79.8816 },
  { name: 'Wattala', province: 'Western', lat: 6.9895, lon: 79.8931 },
  { name: 'Ja-Ela', province: 'Western', lat: 7.0744, lon: 79.8917 },
  { name: 'Negombo', province: 'Western', lat: 7.2083, lon: 79.8358 },
  { name: 'Gampaha', province: 'Western', lat: 7.0917, lon: 80.0000 },
  { name: 'Kaduwela', province: 'Western', lat: 6.9339, lon: 79.9847 },
  { name: 'Homagama', province: 'Western', lat: 6.8444, lon: 80.0025 },
  { name: 'Panadura', province: 'Western', lat: 6.7130, lon: 79.9026 },
  { name: 'Kalutara', province: 'Western', lat: 6.5854, lon: 79.9607 },
  { name: 'Beruwala', province: 'Western', lat: 6.4788, lon: 79.9828 },

  // Central Province
  { name: 'Kandy', province: 'Central', lat: 7.2906, lon: 80.6337 },
  { name: 'Matale', province: 'Central', lat: 7.4675, lon: 80.6234 },
  { name: 'Nuwara Eliya', province: 'Central', lat: 6.9497, lon: 80.7891 },

  // Southern Province
  { name: 'Galle', province: 'Southern', lat: 6.0535, lon: 80.2210 },
  { name: 'Ambalangoda', province: 'Southern', lat: 6.2354, lon: 80.0540 },
  { name: 'Weligama', province: 'Southern', lat: 5.9739, lon: 80.4297 },
  { name: 'Matara', province: 'Southern', lat: 5.9549, lon: 80.5550 },
  { name: 'Tangalle', province: 'Southern', lat: 6.0242, lon: 80.7947 },
  { name: 'Hambantota', province: 'Southern', lat: 6.1246, lon: 81.1185 },

  // Northern Province
  { name: 'Jaffna', province: 'Northern', lat: 9.6615, lon: 80.0255 },
  { name: 'Point Pedro', province: 'Northern', lat: 9.8167, lon: 80.2333 },
  { name: 'Kilinochchi', province: 'Northern', lat: 9.3961, lon: 80.3982 },
  { name: 'Mannar', province: 'Northern', lat: 8.9810, lon: 79.9044 },
  { name: 'Vavuniya', province: 'Northern', lat: 8.7514, lon: 80.4971 },
  { name: 'Mullaitivu', province: 'Northern', lat: 9.2671, lon: 80.8142 },

  // Eastern Province
  { name: 'Trincomalee', province: 'Eastern', lat: 8.5874, lon: 81.2152 },
  { name: 'Batticaloa', province: 'Eastern', lat: 7.7170, lon: 81.7000 },
  { name: 'Kalmunai', province: 'Eastern', lat: 7.4167, lon: 81.8167 },
  { name: 'Ampara', province: 'Eastern', lat: 7.2975, lon: 81.6747 },

  // North Western Province
  { name: 'Kurunegala', province: 'North Western', lat: 7.4863, lon: 80.3647 },
  { name: 'Puttalam', province: 'North Western', lat: 8.0362, lon: 79.8283 },
  { name: 'Chilaw', province: 'North Western', lat: 7.5759, lon: 79.7952 },

  // North Central Province
  { name: 'Anuradhapura', province: 'North Central', lat: 8.3114, lon: 80.4037 },
  { name: 'Polonnaruwa', province: 'North Central', lat: 7.9403, lon: 81.0188 },

  // Uva Province
  { name: 'Badulla', province: 'Uva', lat: 6.9934, lon: 81.0550 },
  { name: 'Bandarawela', province: 'Uva', lat: 6.8333, lon: 80.9833 },
  { name: 'Monaragala', province: 'Uva', lat: 6.8714, lon: 81.3507 },

  // Sabaragamuwa Province
  { name: 'Ratnapura', province: 'Sabaragamuwa', lat: 6.6828, lon: 80.3992 },
  { name: 'Kegalle', province: 'Sabaragamuwa', lat: 7.2513, lon: 80.3464 },
  { name: 'Embilipitiya', province: 'Sabaragamuwa', lat: 6.3439, lon: 80.8500 },
];

/** Groups the flat list into { province: [locations...] }, in the order provinces first appear. */
export function groupByProvince(locations = SRI_LANKA_LOCATIONS) {
  const groups = new Map();
  for (const loc of locations) {
    if (!groups.has(loc.province)) groups.set(loc.province, []);
    groups.get(loc.province).push(loc);
  }
  return groups;
}

export function findLocation(name) {
  return SRI_LANKA_LOCATIONS.find((l) => l.name === name) || null;
}
