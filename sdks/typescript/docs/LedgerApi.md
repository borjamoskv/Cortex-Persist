# LedgerApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createCheckpointV1LedgerCheckpointPost**](LedgerApi.md#createcheckpointv1ledgercheckpointpost) | **POST** /v1/ledger/checkpoint | Create Checkpoint |
| [**getLedgerStatusV1LedgerStatusGet**](LedgerApi.md#getledgerstatusv1ledgerstatusget) | **GET** /v1/ledger/status | Get Ledger Status |
| [**verifyLedgerV1LedgerVerifyGet**](LedgerApi.md#verifyledgerv1ledgerverifyget) | **GET** /v1/ledger/verify | Verify Ledger |



## createCheckpointV1LedgerCheckpointPost

> CheckpointResponse createCheckpointV1LedgerCheckpointPost(authorization)

Create Checkpoint

Manually trigger a Merkle root checkpoint for recent transactions.

### Example

```ts
import {
  Configuration,
  LedgerApi,
} from '';
import type { CreateCheckpointV1LedgerCheckpointPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new LedgerApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies CreateCheckpointV1LedgerCheckpointPostRequest;

  try {
    const data = await api.createCheckpointV1LedgerCheckpointPost(body);
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

[**CheckpointResponse**](CheckpointResponse.md)

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


## getLedgerStatusV1LedgerStatusGet

> LedgerReportResponse getLedgerStatusV1LedgerStatusGet(authorization)

Get Ledger Status

Check the cryptographic integrity of all ledgers (Tx and Votes).

### Example

```ts
import {
  Configuration,
  LedgerApi,
} from '';
import type { GetLedgerStatusV1LedgerStatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new LedgerApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies GetLedgerStatusV1LedgerStatusGetRequest;

  try {
    const data = await api.getLedgerStatusV1LedgerStatusGet(body);
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

[**LedgerReportResponse**](LedgerReportResponse.md)

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


## verifyLedgerV1LedgerVerifyGet

> LedgerReportResponse verifyLedgerV1LedgerVerifyGet(authorization)

Verify Ledger

Alias for /status - performs full integrity verification.

### Example

```ts
import {
  Configuration,
  LedgerApi,
} from '';
import type { VerifyLedgerV1LedgerVerifyGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new LedgerApi();

  const body = {
    // string | Bearer <api-key> (optional)
    authorization: authorization_example,
  } satisfies VerifyLedgerV1LedgerVerifyGetRequest;

  try {
    const data = await api.verifyLedgerV1LedgerVerifyGet(body);
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

[**LedgerReportResponse**](LedgerReportResponse.md)

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

