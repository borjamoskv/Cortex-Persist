
# FactResponse


## Properties

Name | Type
------------ | -------------
`id` | number
`project` | string
`content` | string
`factType` | string
`tags` | Array&lt;string&gt;
`createdAt` | string
`updatedAt` | string
`confidence` | [Confidence](Confidence.md)
`validFrom` | string
`validUntil` | string
`source` | string
`meta` | { [key: string]: any; }
`isTombstoned` | boolean
`hash` | string
`txId` | string
`consensusScore` | number

## Example

```typescript
import type { FactResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "project": null,
  "content": null,
  "factType": null,
  "tags": null,
  "createdAt": null,
  "updatedAt": null,
  "confidence": null,
  "validFrom": null,
  "validUntil": null,
  "source": null,
  "meta": null,
  "isTombstoned": null,
  "hash": null,
  "txId": null,
  "consensusScore": null,
} satisfies FactResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FactResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


