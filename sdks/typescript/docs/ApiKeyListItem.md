
# ApiKeyListItem

Non-sensitive API key metadata.

## Properties

Name | Type
------------ | -------------
`id` | string
`name` | string
`prefix` | string
`tenantId` | string
`permissions` | Array&lt;string&gt;
`isActive` | boolean
`createdAt` | string
`lastUsed` | string

## Example

```typescript
import type { ApiKeyListItem } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "name": null,
  "prefix": null,
  "tenantId": null,
  "permissions": null,
  "isActive": null,
  "createdAt": null,
  "lastUsed": null,
} satisfies ApiKeyListItem

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ApiKeyListItem
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


