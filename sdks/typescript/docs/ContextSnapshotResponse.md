
# ContextSnapshotResponse


## Properties

Name | Type
------------ | -------------
`activeProject` | string
`confidence` | string
`signalsUsed` | number
`summary` | string
`topSignals` | [Array&lt;ContextSignalModel&gt;](ContextSignalModel.md)
`projectsRanked` | [Array&lt;ProjectScoreModel&gt;](ProjectScoreModel.md)

## Example

```typescript
import type { ContextSnapshotResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "activeProject": null,
  "confidence": null,
  "signalsUsed": null,
  "summary": null,
  "topSignals": null,
  "projectsRanked": null,
} satisfies ContextSnapshotResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ContextSnapshotResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


