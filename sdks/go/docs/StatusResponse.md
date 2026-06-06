# StatusResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Version** | **string** |  | 
**TotalFacts** | **int32** |  | 
**ActiveFacts** | **int32** |  | 
**Deprecated** | **int32** |  | 
**Projects** | **int32** |  | 
**Embeddings** | **int32** |  | 
**Transactions** | **int32** |  | 
**DbSizeMb** | **float32** |  | 

## Methods

### NewStatusResponse

`func NewStatusResponse(version string, totalFacts int32, activeFacts int32, deprecated int32, projects int32, embeddings int32, transactions int32, dbSizeMb float32, ) *StatusResponse`

NewStatusResponse instantiates a new StatusResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewStatusResponseWithDefaults

`func NewStatusResponseWithDefaults() *StatusResponse`

NewStatusResponseWithDefaults instantiates a new StatusResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetVersion

`func (o *StatusResponse) GetVersion() string`

GetVersion returns the Version field if non-nil, zero value otherwise.

### GetVersionOk

`func (o *StatusResponse) GetVersionOk() (*string, bool)`

GetVersionOk returns a tuple with the Version field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVersion

`func (o *StatusResponse) SetVersion(v string)`

SetVersion sets Version field to given value.


### GetTotalFacts

`func (o *StatusResponse) GetTotalFacts() int32`

GetTotalFacts returns the TotalFacts field if non-nil, zero value otherwise.

### GetTotalFactsOk

`func (o *StatusResponse) GetTotalFactsOk() (*int32, bool)`

GetTotalFactsOk returns a tuple with the TotalFacts field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalFacts

`func (o *StatusResponse) SetTotalFacts(v int32)`

SetTotalFacts sets TotalFacts field to given value.


### GetActiveFacts

`func (o *StatusResponse) GetActiveFacts() int32`

GetActiveFacts returns the ActiveFacts field if non-nil, zero value otherwise.

### GetActiveFactsOk

`func (o *StatusResponse) GetActiveFactsOk() (*int32, bool)`

GetActiveFactsOk returns a tuple with the ActiveFacts field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActiveFacts

`func (o *StatusResponse) SetActiveFacts(v int32)`

SetActiveFacts sets ActiveFacts field to given value.


### GetDeprecated

`func (o *StatusResponse) GetDeprecated() int32`

GetDeprecated returns the Deprecated field if non-nil, zero value otherwise.

### GetDeprecatedOk

`func (o *StatusResponse) GetDeprecatedOk() (*int32, bool)`

GetDeprecatedOk returns a tuple with the Deprecated field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeprecated

`func (o *StatusResponse) SetDeprecated(v int32)`

SetDeprecated sets Deprecated field to given value.


### GetProjects

`func (o *StatusResponse) GetProjects() int32`

GetProjects returns the Projects field if non-nil, zero value otherwise.

### GetProjectsOk

`func (o *StatusResponse) GetProjectsOk() (*int32, bool)`

GetProjectsOk returns a tuple with the Projects field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProjects

`func (o *StatusResponse) SetProjects(v int32)`

SetProjects sets Projects field to given value.


### GetEmbeddings

`func (o *StatusResponse) GetEmbeddings() int32`

GetEmbeddings returns the Embeddings field if non-nil, zero value otherwise.

### GetEmbeddingsOk

`func (o *StatusResponse) GetEmbeddingsOk() (*int32, bool)`

GetEmbeddingsOk returns a tuple with the Embeddings field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEmbeddings

`func (o *StatusResponse) SetEmbeddings(v int32)`

SetEmbeddings sets Embeddings field to given value.


### GetTransactions

`func (o *StatusResponse) GetTransactions() int32`

GetTransactions returns the Transactions field if non-nil, zero value otherwise.

### GetTransactionsOk

`func (o *StatusResponse) GetTransactionsOk() (*int32, bool)`

GetTransactionsOk returns a tuple with the Transactions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTransactions

`func (o *StatusResponse) SetTransactions(v int32)`

SetTransactions sets Transactions field to given value.


### GetDbSizeMb

`func (o *StatusResponse) GetDbSizeMb() float32`

GetDbSizeMb returns the DbSizeMb field if non-nil, zero value otherwise.

### GetDbSizeMbOk

`func (o *StatusResponse) GetDbSizeMbOk() (*float32, bool)`

GetDbSizeMbOk returns a tuple with the DbSizeMb field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDbSizeMb

`func (o *StatusResponse) SetDbSizeMb(v float32)`

SetDbSizeMb sets DbSizeMb field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


