# \LedgerApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_checkpoint_v1_ledger_checkpoint_post**](LedgerApi.md#create_checkpoint_v1_ledger_checkpoint_post) | **POST** /v1/ledger/checkpoint | Create Checkpoint
[**get_ledger_status_v1_ledger_status_get**](LedgerApi.md#get_ledger_status_v1_ledger_status_get) | **GET** /v1/ledger/status | Get Ledger Status
[**verify_ledger_v1_ledger_verify_get**](LedgerApi.md#verify_ledger_v1_ledger_verify_get) | **GET** /v1/ledger/verify | Verify Ledger



## create_checkpoint_v1_ledger_checkpoint_post

> models::CheckpointResponse create_checkpoint_v1_ledger_checkpoint_post(authorization)
Create Checkpoint

Manually trigger a Merkle root checkpoint for recent transactions.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::CheckpointResponse**](CheckpointResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## get_ledger_status_v1_ledger_status_get

> models::LedgerReportResponse get_ledger_status_v1_ledger_status_get(authorization)
Get Ledger Status

Check the cryptographic integrity of all ledgers (Tx and Votes).

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::LedgerReportResponse**](LedgerReportResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)


## verify_ledger_v1_ledger_verify_get

> models::LedgerReportResponse verify_ledger_v1_ledger_verify_get(authorization)
Verify Ledger

Alias for /status - performs full integrity verification.

### Parameters


Name | Type | Description  | Required | Notes
------------- | ------------- | ------------- | ------------- | -------------
**authorization** | Option<**String**> | Bearer <api-key> |  |

### Return type

[**models::LedgerReportResponse**](LedgerReportResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

