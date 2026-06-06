# MissionsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**launchMissionV1MissionsLaunchPost**](MissionsApi.md#launchmissionv1missionslaunchpost) | **POST** /v1/missions/launch | Launch Mission |
| [**listMissionsV1MissionsGet**](MissionsApi.md#listmissionsv1missionsget) | **GET** /v1/missions/ | List Missions |



## launchMissionV1MissionsLaunchPost

> MissionResponse launchMissionV1MissionsLaunchPost(missionLaunchRequest, authorization)

Launch Mission

Launch a new swarm mission through the CORTEX Launchpad.

### Example

```ts
import {
  Configuration,
  MissionsApi,
} from '';
import type { LaunchMissionV1MissionsLaunchPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MissionsApi();

  const body = {
    // MissionLaunchRequest
    missionLaunchRequest: ...,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies LaunchMissionV1MissionsLaunchPostRequest;

  try {
    const data = await api.launchMissionV1MissionsLaunchPost(body);
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
| **missionLaunchRequest** | [MissionLaunchRequest](MissionLaunchRequest.md) |  | |
| **authorization** | `string` | Bearer &lt;api-key&gt; | [Optional] [Defaults to `undefined`] |

### Return type

[**MissionResponse**](MissionResponse.md)

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


## listMissionsV1MissionsGet

> Array&lt;{ [key: string]: any; }&gt; listMissionsV1MissionsGet(project, authorization)

List Missions

List recent mission intents and reports from the ledger.

### Example

```ts
import {
  Configuration,
  MissionsApi,
} from '';
import type { ListMissionsV1MissionsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MissionsApi();

  const body = {
    // string (optional)
    project: project_example,
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies ListMissionsV1MissionsGetRequest;

  try {
    const data = await api.listMissionsV1MissionsGet(body);
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
| **project** | `string` |  | [Optional] [Defaults to `undefined`] |
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

