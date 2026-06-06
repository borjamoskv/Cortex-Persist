# SwarmApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createWorktreeV1SwarmWorktreesPost**](SwarmApi.md#createworktreev1swarmworktreespost) | **POST** /v1/swarm/worktrees | Create Worktree |
| [**deleteWorktreeV1SwarmWorktreesWorktreeIdDelete**](SwarmApi.md#deleteworktreev1swarmworktreesworktreeiddelete) | **DELETE** /v1/swarm/worktrees/{worktree_id} | Delete Worktree |
| [**getSwarmStatusV1SwarmStatusGet**](SwarmApi.md#getswarmstatusv1swarmstatusget) | **GET** /v1/swarm/status | Get Swarm Status |
| [**getWorktreeStatusV1SwarmWorktreesWorktreeIdGet**](SwarmApi.md#getworktreestatusv1swarmworktreesworktreeidget) | **GET** /v1/swarm/worktrees/{worktree_id} | Get Worktree Status |
| [**runPsychohistorySimulationV1SwarmPsychohistoryPost**](SwarmApi.md#runpsychohistorysimulationv1swarmpsychohistorypost) | **POST** /v1/swarm/psychohistory | Run Psychohistory Simulation |



## createWorktreeV1SwarmWorktreesPost

> WorktreeResponse createWorktreeV1SwarmWorktreesPost(worktreeCreateRequest, authorization)

Create Worktree

Provision a new isolated execution environment (Hito 3).

### Example

```ts
import {
  Configuration,
  SwarmApi,
} from '';
import type { CreateWorktreeV1SwarmWorktreesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SwarmApi();

  const body = {
    // WorktreeCreateRequest
    worktreeCreateRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies CreateWorktreeV1SwarmWorktreesPostRequest;

  try {
    const data = await api.createWorktreeV1SwarmWorktreesPost(body);
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
| **worktreeCreateRequest** | [WorktreeCreateRequest](WorktreeCreateRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**WorktreeResponse**](WorktreeResponse.md)

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


## deleteWorktreeV1SwarmWorktreesWorktreeIdDelete

> any deleteWorktreeV1SwarmWorktreesWorktreeIdDelete(worktreeId, authorization)

Delete Worktree

Cleanly destroy an isolated worktree.

### Example

```ts
import {
  Configuration,
  SwarmApi,
} from '';
import type { DeleteWorktreeV1SwarmWorktreesWorktreeIdDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SwarmApi();

  const body = {
    // string
    worktreeId: worktreeId_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies DeleteWorktreeV1SwarmWorktreesWorktreeIdDeleteRequest;

  try {
    const data = await api.deleteWorktreeV1SwarmWorktreesWorktreeIdDelete(body);
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
| **worktreeId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**any**

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


## getSwarmStatusV1SwarmStatusGet

> SwarmStatusResponse getSwarmStatusV1SwarmStatusGet(authorization)

Get Swarm Status

Aggregate swarm health and load metrics.

### Example

```ts
import {
  Configuration,
  SwarmApi,
} from '';
import type { GetSwarmStatusV1SwarmStatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SwarmApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetSwarmStatusV1SwarmStatusGetRequest;

  try {
    const data = await api.getSwarmStatusV1SwarmStatusGet(body);
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

[**SwarmStatusResponse**](SwarmStatusResponse.md)

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


## getWorktreeStatusV1SwarmWorktreesWorktreeIdGet

> WorktreeResponse getWorktreeStatusV1SwarmWorktreesWorktreeIdGet(worktreeId, authorization)

Get Worktree Status

Get metadata for a specific worktree.

### Example

```ts
import {
  Configuration,
  SwarmApi,
} from '';
import type { GetWorktreeStatusV1SwarmWorktreesWorktreeIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SwarmApi();

  const body = {
    // string
    worktreeId: worktreeId_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetWorktreeStatusV1SwarmWorktreesWorktreeIdGetRequest;

  try {
    const data = await api.getWorktreeStatusV1SwarmWorktreesWorktreeIdGet(body);
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
| **worktreeId** | `string` |  | [Defaults to `undefined`] |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**WorktreeResponse**](WorktreeResponse.md)

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


## runPsychohistorySimulationV1SwarmPsychohistoryPost

> any runPsychohistorySimulationV1SwarmPsychohistoryPost(psychohistoryRequest, authorization)

Run Psychohistory Simulation

Trigger the Psychohistory Fracture Simulator (Hito 4). Orchestrates 50 specialized agents using a Semaphore to calculate catastrophic cascades. Extracts a Byzantine consensus O(1) Contingency Crystal.

### Example

```ts
import {
  Configuration,
  SwarmApi,
} from '';
import type { RunPsychohistorySimulationV1SwarmPsychohistoryPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new SwarmApi();

  const body = {
    // PsychohistoryRequest
    psychohistoryRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies RunPsychohistorySimulationV1SwarmPsychohistoryPostRequest;

  try {
    const data = await api.runPsychohistorySimulationV1SwarmPsychohistoryPost(body);
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
| **psychohistoryRequest** | [PsychohistoryRequest](PsychohistoryRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

**any**

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

