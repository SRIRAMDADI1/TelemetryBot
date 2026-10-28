param collectorName string = 'telemetrybot-collector'
param location string = 'eastus'
param postgresSku string = 'Standard_B1ms'

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-telemetrybot'
  location: location
}

// Stub: wire Azure Container Apps + Azure Database for PostgreSQL Flexible Server
// in a follow-up deploy. Local docker-compose remains the F1 acceptance path.

output resourceGroupName string = rg.name
output note string = 'F1 stub — replace with Container Apps + Flexible Server modules when promoting to Azure.'
