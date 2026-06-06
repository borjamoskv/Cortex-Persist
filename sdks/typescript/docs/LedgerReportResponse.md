
# LedgerReportResponse


## Properties

Name | Type
------------ | -------------
`valid` | boolean
`violations` | Array&lt;{ [key: string]: any; } | null&gt;
`txChecked` | number
`rootsChecked` | number
`votesChecked` | number
`voteCheckpointsChecked` | number

## Example

```typescript
import type { LedgerReportResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "valid": null,
  "violations": null,
  "txChecked": null,
  "rootsChecked": null,
  "votesChecked": null,
  "voteCheckpointsChecked": null,
} satisfies LedgerReportResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as LedgerReportResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


