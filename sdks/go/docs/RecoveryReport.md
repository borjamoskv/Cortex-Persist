# RecoveryReport

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Status** | **string** |  | 
**RecoveredItems** | **int32** |  | 
**FailedItems** | **int32** |  | 
**LastCheckpointId** | Pointer to **NullableString** |  | [optional] 
**Warnings** | Pointer to **[]string** |  | [optional] 

## Methods

### NewRecoveryReport

`func NewRecoveryReport(status string, recoveredItems int32, failedItems int32, ) *RecoveryReport`

NewRecoveryReport instantiates a new RecoveryReport object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRecoveryReportWithDefaults

`func NewRecoveryReportWithDefaults() *RecoveryReport`

NewRecoveryReportWithDefaults instantiates a new RecoveryReport object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetStatus

`func (o *RecoveryReport) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *RecoveryReport) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *RecoveryReport) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetRecoveredItems

`func (o *RecoveryReport) GetRecoveredItems() int32`

GetRecoveredItems returns the RecoveredItems field if non-nil, zero value otherwise.

### GetRecoveredItemsOk

`func (o *RecoveryReport) GetRecoveredItemsOk() (*int32, bool)`

GetRecoveredItemsOk returns a tuple with the RecoveredItems field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRecoveredItems

`func (o *RecoveryReport) SetRecoveredItems(v int32)`

SetRecoveredItems sets RecoveredItems field to given value.


### GetFailedItems

`func (o *RecoveryReport) GetFailedItems() int32`

GetFailedItems returns the FailedItems field if non-nil, zero value otherwise.

### GetFailedItemsOk

`func (o *RecoveryReport) GetFailedItemsOk() (*int32, bool)`

GetFailedItemsOk returns a tuple with the FailedItems field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFailedItems

`func (o *RecoveryReport) SetFailedItems(v int32)`

SetFailedItems sets FailedItems field to given value.


### GetLastCheckpointId

`func (o *RecoveryReport) GetLastCheckpointId() string`

GetLastCheckpointId returns the LastCheckpointId field if non-nil, zero value otherwise.

### GetLastCheckpointIdOk

`func (o *RecoveryReport) GetLastCheckpointIdOk() (*string, bool)`

GetLastCheckpointIdOk returns a tuple with the LastCheckpointId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastCheckpointId

`func (o *RecoveryReport) SetLastCheckpointId(v string)`

SetLastCheckpointId sets LastCheckpointId field to given value.

### HasLastCheckpointId

`func (o *RecoveryReport) HasLastCheckpointId() bool`

HasLastCheckpointId returns a boolean if a field has been set.

### SetLastCheckpointIdNil

`func (o *RecoveryReport) SetLastCheckpointIdNil(b bool)`

 SetLastCheckpointIdNil sets the value for LastCheckpointId to be an explicit nil

### UnsetLastCheckpointId
`func (o *RecoveryReport) UnsetLastCheckpointId()`

UnsetLastCheckpointId ensures that no value is present for LastCheckpointId, not even an explicit nil
### GetWarnings

`func (o *RecoveryReport) GetWarnings() []string`

GetWarnings returns the Warnings field if non-nil, zero value otherwise.

### GetWarningsOk

`func (o *RecoveryReport) GetWarningsOk() (*[]string, bool)`

GetWarningsOk returns a tuple with the Warnings field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWarnings

`func (o *RecoveryReport) SetWarnings(v []string)`

SetWarnings sets Warnings field to given value.

### HasWarnings

`func (o *RecoveryReport) HasWarnings() bool`

HasWarnings returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


