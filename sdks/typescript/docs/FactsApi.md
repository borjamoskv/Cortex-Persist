# FactsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**batchStoreV1FactsBatchPost**](FactsApi.md#batchstorev1factsbatchpost) | **POST** /v1/facts/batch | Batch Store |
| [**castVoteV1FactsFactIdVotePost**](FactsApi.md#castvotev1factsfactidvotepost) | **POST** /v1/facts/{fact_id}/vote | Cast Vote |
| [**castVoteV2V1FactsFactIdVoteV2Post**](FactsApi.md#castvotev2v1factsfactidvotev2post) | **POST** /v1/facts/{fact_id}/vote-v2 | Cast Vote V2 |
| [**deprecateFactV1FactsFactIdDelete**](FactsApi.md#deprecatefactv1factsfactiddelete) | **DELETE** /v1/facts/{fact_id} | Deprecate Fact |
| [**getCausalChainV1FactsFactIdChainGet**](FactsApi.md#getcausalchainv1factsfactidchainget) | **GET** /v1/facts/{fact_id}/chain | Get Causal Chain |
| [**getFactByIdV1FactsFactIdGet**](FactsApi.md#getfactbyidv1factsfactidget) | **GET** /v1/facts/{fact_id} | Get Fact By Id |
| [**getFactHistoryV1FactsFactIdHistoryGet**](FactsApi.md#getfacthistoryv1factsfactidhistoryget) | **GET** /v1/facts/{fact_id}/history | Get Fact History |
| [**listAllFactsV1FactsGet**](FactsApi.md#listallfactsv1factsget) | **GET** /v1/facts | List All Facts |
| [**listVotesV1FactsFactIdVotesGet**](FactsApi.md#listvotesv1factsfactidvotesget) | **GET** /v1/facts/{fact_id}/votes | List Votes |
| [**propagateTaintV1FactsFactIdTaintPost**](FactsApi.md#propagatetaintv1factsfactidtaintpost) | **POST** /v1/facts/{fact_id}/taint | Propagate Taint |
| [**recallFactsV1ProjectsProjectFactsGet**](FactsApi.md#recallfactsv1projectsprojectfactsget) | **GET** /v1/projects/{project}/facts | Recall Facts |
| [**searchFactsV1FactsSearchPost**](FactsApi.md#searchfactsv1factssearchpost) | **POST** /v1/facts/search | Search Facts |
| [**storeFactV1FactsPost**](FactsApi.md#storefactv1factspost) | **POST** /v1/facts | Store Fact |
| [**verifyLedgerV1FactsVerifyGet**](FactsApi.md#verifyledgerv1factsverifyget) | **GET** /v1/facts/verify | Verify Ledger |



## batchStoreV1FactsBatchPost

> { [key: string]: any; } batchStoreV1FactsBatchPost(batchStoreRequest, authorization)

Batch Store

Batch store up to 100 facts in a single request.

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { BatchStoreV1FactsBatchPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // BatchStoreRequest
    batchStoreRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies BatchStoreV1FactsBatchPostRequest;

  try {
    const data = await api.batchStoreV1FactsBatchPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **batchStoreRequest** | [BatchStoreRequest](BatchStoreRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## castVoteV1FactsFactIdVotePost

> VoteResponse castVoteV1FactsFactIdVotePost(factId, voteRequest, authorization)

Cast Vote

Cast a consensus vote (verify/dispute) on a fact.

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { CastVoteV1FactsFactIdVotePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number
    factId: 56,
    // VoteRequest
    voteRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies CastVoteV1FactsFactIdVotePostRequest;

  try {
    const data = await api.castVoteV1FactsFactIdVotePost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **factId** | `number` |  | [Defaults to `undefined`] |
| **voteRequest** | [VoteRequest](VoteRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**VoteResponse**](VoteResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## castVoteV2V1FactsFactIdVoteV2Post

> VoteResponse castVoteV2V1FactsFactIdVoteV2Post(factId, voteV2Request, authorization)

Cast Vote V2

Cast a reputation-weighted consensus vote (RWC).

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { CastVoteV2V1FactsFactIdVoteV2PostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number
    factId: 56,
    // VoteV2Request
    voteV2Request: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies CastVoteV2V1FactsFactIdVoteV2PostRequest;

  try {
    const data = await api.castVoteV2V1FactsFactIdVoteV2Post(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **factId** | `number` |  | [Defaults to `undefined`] |
| **voteV2Request** | [VoteV2Request](VoteV2Request.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**VoteResponse**](VoteResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## deprecateFactV1FactsFactIdDelete

> { [key: string]: any; } deprecateFactV1FactsFactIdDelete(factId, authorization)

Deprecate Fact

Soft-deprecate a fact (mark as invalid).

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { DeprecateFactV1FactsFactIdDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number
    factId: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies DeprecateFactV1FactsFactIdDeleteRequest;

  try {
    const data = await api.deprecateFactV1FactsFactIdDelete(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **factId** | `number` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getCausalChainV1FactsFactIdChainGet

> Array&lt;{ [key: string]: any; }&gt; getCausalChainV1FactsFactIdChainGet(factId, direction, maxDepth, authorization)

Get Causal Chain

Get the causal chain for a fact (up&#x3D;ancestors, down&#x3D;descendants).

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { GetCausalChainV1FactsFactIdChainGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number
    factId: 56,
    // string | \'up\' or \'down\' (optional)
    direction: direction_example,
    // number (optional)
    maxDepth: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetCausalChainV1FactsFactIdChainGetRequest;

  try {
    const data = await api.getCausalChainV1FactsFactIdChainGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **factId** | `number` |  | [Defaults to `undefined`] |
| **direction** | `string` | \&#39;up\&#39; or \&#39;down\&#39; | [Optional] [Defaults to `&#39;down&#39;`] |
| **maxDepth** | `number` |  | [Optional] [Defaults to `10`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**Array<{ [key: string]: any; }>**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getFactByIdV1FactsFactIdGet

> FactResponse getFactByIdV1FactsFactIdGet(factId, authorization)

Get Fact By Id

Get a single fact by ID.

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { GetFactByIdV1FactsFactIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number
    factId: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetFactByIdV1FactsFactIdGetRequest;

  try {
    const data = await api.getFactByIdV1FactsFactIdGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **factId** | `number` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**FactResponse**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getFactHistoryV1FactsFactIdHistoryGet

> Array&lt;FactResponse&gt; getFactHistoryV1FactsFactIdHistoryGet(factId, authorization)

Get Fact History

Retrieve version history for a specific fact.

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { GetFactHistoryV1FactsFactIdHistoryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number
    factId: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetFactHistoryV1FactsFactIdHistoryGetRequest;

  try {
    const data = await api.getFactHistoryV1FactsFactIdHistoryGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **factId** | `number` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;FactResponse&gt;**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listAllFactsV1FactsGet

> Array&lt;FactResponse&gt; listAllFactsV1FactsGet(limit, authorization)

List All Facts

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { ListAllFactsV1FactsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ListAllFactsV1FactsGetRequest;

  try {
    const data = await api.listAllFactsV1FactsGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **limit** | `number` |  | [Optional] [Defaults to `50`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;FactResponse&gt;**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listVotesV1FactsFactIdVotesGet

> Array&lt;{ [key: string]: any; }&gt; listVotesV1FactsFactIdVotesGet(factId, authorization)

List Votes

Retrieve all votes for a specific fact (Tenant Isolated).

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { ListVotesV1FactsFactIdVotesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number
    factId: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ListVotesV1FactsFactIdVotesGetRequest;

  try {
    const data = await api.listVotesV1FactsFactIdVotesGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **factId** | `number` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**Array<{ [key: string]: any; }>**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## propagateTaintV1FactsFactIdTaintPost

> { [key: string]: any; } propagateTaintV1FactsFactIdTaintPost(factId, authorization)

Propagate Taint

Trigger Ω₁₃ taint propagation from a compromised/invalidated fact.

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { PropagateTaintV1FactsFactIdTaintPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // number
    factId: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies PropagateTaintV1FactsFactIdTaintPostRequest;

  try {
    const data = await api.propagateTaintV1FactsFactIdTaintPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **factId** | `number` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## recallFactsV1ProjectsProjectFactsGet

> Array&lt;FactResponse&gt; recallFactsV1ProjectsProjectFactsGet(project, limit, authorization)

Recall Facts

Recall facts for a specific project with tenant isolation.

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { RecallFactsV1ProjectsProjectFactsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // string
    project: project_example,
    // number (optional)
    limit: 56,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies RecallFactsV1ProjectsProjectFactsGetRequest;

  try {
    const data = await api.recallFactsV1ProjectsProjectFactsGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **project** | `string` |  | [Defaults to `undefined`] |
| **limit** | `number` |  | [Optional] [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;FactResponse&gt;**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## searchFactsV1FactsSearchPost

> Array&lt;FactResponse&gt; searchFactsV1FactsSearchPost(searchMemoryRequest, authorization)

Search Facts

Semantic search across all facts (scoped to tenant).

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { SearchFactsV1FactsSearchPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // SearchMemoryRequest
    searchMemoryRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies SearchFactsV1FactsSearchPostRequest;

  try {
    const data = await api.searchFactsV1FactsSearchPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **searchMemoryRequest** | [SearchMemoryRequest](SearchMemoryRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;FactResponse&gt;**](FactResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## storeFactV1FactsPost

> StoreResponse storeFactV1FactsPost(storeRequest, authorization)

Store Fact

Store a fact (scoped to authenticated tenant).

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { StoreFactV1FactsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // StoreRequest
    storeRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies StoreFactV1FactsPostRequest;

  try {
    const data = await api.storeFactV1FactsPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **storeRequest** | [StoreRequest](StoreRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**StoreResponse**](StoreResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## verifyLedgerV1FactsVerifyGet

> { [key: string]: any; } verifyLedgerV1FactsVerifyGet(authorization)

Verify Ledger

Verify cryptographic integrity of the memory ledger.

### Example

```ts
import {
  Configuration,
  FactsApi,
} from '';
import type { VerifyLedgerV1FactsVerifyGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new FactsApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies VerifyLedgerV1FactsVerifyGetRequest;

  try {
    const data = await api.verifyLedgerV1FactsVerifyGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

