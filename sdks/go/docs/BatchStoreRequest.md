# BatchStoreRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Memories** | [**[]StoreMemoryRequest**](StoreMemoryRequest.md) |  | 

## Methods

### NewBatchStoreRequest

`func NewBatchStoreRequest(memories []StoreMemoryRequest, ) *BatchStoreRequest`

NewBatchStoreRequest instantiates a new BatchStoreRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBatchStoreRequestWithDefaults

`func NewBatchStoreRequestWithDefaults() *BatchStoreRequest`

NewBatchStoreRequestWithDefaults instantiates a new BatchStoreRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetMemories

`func (o *BatchStoreRequest) GetMemories() []StoreMemoryRequest`

GetMemories returns the Memories field if non-nil, zero value otherwise.

### GetMemoriesOk

`func (o *BatchStoreRequest) GetMemoriesOk() (*[]StoreMemoryRequest, bool)`

GetMemoriesOk returns a tuple with the Memories field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMemories

`func (o *BatchStoreRequest) SetMemories(v []StoreMemoryRequest)`

SetMemories sets Memories field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


