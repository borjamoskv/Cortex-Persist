
# ComplianceReport


## Properties

Name | Type
------------ | -------------
`status` | string
`ledgerValid` | boolean
`totalTrustScore` | number
`auditCoverage` | number
`complianceLevel` | string
`article12Status` | string

## Example

```typescript
import type { ComplianceReport } from ''

// TODO: Update the object below with actual values
const example = {
  "status": null,
  "ledgerValid": null,
  "totalTrustScore": null,
  "auditCoverage": null,
  "complianceLevel": null,
  "article12Status": null,
} satisfies ComplianceReport

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ComplianceReport
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


