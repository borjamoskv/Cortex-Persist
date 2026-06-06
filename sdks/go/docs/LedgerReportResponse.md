# LedgerReportResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Valid** | **bool** |  | 
**Violations** | **[]map[string]interface{}** |  | 
**TxChecked** | Pointer to **int32** |  | [optional] [default to 0]
**RootsChecked** | Pointer to **int32** |  | [optional] [default to 0]
**VotesChecked** | Pointer to **int32** |  | [optional] [default to 0]
**VoteCheckpointsChecked** | Pointer to **int32** |  | [optional] [default to 0]

## Methods

### NewLedgerReportResponse

`func NewLedgerReportResponse(valid bool, violations []*map[string]interface{}, ) *LedgerReportResponse`

NewLedgerReportResponse instantiates a new LedgerReportResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewLedgerReportResponseWithDefaults

`func NewLedgerReportResponseWithDefaults() *LedgerReportResponse`

NewLedgerReportResponseWithDefaults instantiates a new LedgerReportResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetValid

`func (o *LedgerReportResponse) GetValid() bool`

GetValid returns the Valid field if non-nil, zero value otherwise.

### GetValidOk

`func (o *LedgerReportResponse) GetValidOk() (*bool, bool)`

GetValidOk returns a tuple with the Valid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetValid

`func (o *LedgerReportResponse) SetValid(v bool)`

SetValid sets Valid field to given value.


### GetViolations

`func (o *LedgerReportResponse) GetViolations() []*map[string]interface{}`

GetViolations returns the Violations field if non-nil, zero value otherwise.

### GetViolationsOk

`func (o *LedgerReportResponse) GetViolationsOk() (*[]*map[string]interface{}, bool)`

GetViolationsOk returns a tuple with the Violations field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetViolations

`func (o *LedgerReportResponse) SetViolations(v []*map[string]interface{})`

SetViolations sets Violations field to given value.


### GetTxChecked

`func (o *LedgerReportResponse) GetTxChecked() int32`

GetTxChecked returns the TxChecked field if non-nil, zero value otherwise.

### GetTxCheckedOk

`func (o *LedgerReportResponse) GetTxCheckedOk() (*int32, bool)`

GetTxCheckedOk returns a tuple with the TxChecked field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTxChecked

`func (o *LedgerReportResponse) SetTxChecked(v int32)`

SetTxChecked sets TxChecked field to given value.

### HasTxChecked

`func (o *LedgerReportResponse) HasTxChecked() bool`

HasTxChecked returns a boolean if a field has been set.

### GetRootsChecked

`func (o *LedgerReportResponse) GetRootsChecked() int32`

GetRootsChecked returns the RootsChecked field if non-nil, zero value otherwise.

### GetRootsCheckedOk

`func (o *LedgerReportResponse) GetRootsCheckedOk() (*int32, bool)`

GetRootsCheckedOk returns a tuple with the RootsChecked field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRootsChecked

`func (o *LedgerReportResponse) SetRootsChecked(v int32)`

SetRootsChecked sets RootsChecked field to given value.

### HasRootsChecked

`func (o *LedgerReportResponse) HasRootsChecked() bool`

HasRootsChecked returns a boolean if a field has been set.

### GetVotesChecked

`func (o *LedgerReportResponse) GetVotesChecked() int32`

GetVotesChecked returns the VotesChecked field if non-nil, zero value otherwise.

### GetVotesCheckedOk

`func (o *LedgerReportResponse) GetVotesCheckedOk() (*int32, bool)`

GetVotesCheckedOk returns a tuple with the VotesChecked field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVotesChecked

`func (o *LedgerReportResponse) SetVotesChecked(v int32)`

SetVotesChecked sets VotesChecked field to given value.

### HasVotesChecked

`func (o *LedgerReportResponse) HasVotesChecked() bool`

HasVotesChecked returns a boolean if a field has been set.

### GetVoteCheckpointsChecked

`func (o *LedgerReportResponse) GetVoteCheckpointsChecked() int32`

GetVoteCheckpointsChecked returns the VoteCheckpointsChecked field if non-nil, zero value otherwise.

### GetVoteCheckpointsCheckedOk

`func (o *LedgerReportResponse) GetVoteCheckpointsCheckedOk() (*int32, bool)`

GetVoteCheckpointsCheckedOk returns a tuple with the VoteCheckpointsChecked field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVoteCheckpointsChecked

`func (o *LedgerReportResponse) SetVoteCheckpointsChecked(v int32)`

SetVoteCheckpointsChecked sets VoteCheckpointsChecked field to given value.

### HasVoteCheckpointsChecked

`func (o *LedgerReportResponse) HasVoteCheckpointsChecked() bool`

HasVoteCheckpointsChecked returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


