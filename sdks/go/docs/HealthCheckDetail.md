# HealthCheckDetail

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Status** | **string** |  | 
**Detail** | Pointer to **NullableString** |  | [optional] 
**Version** | Pointer to **NullableString** |  | [optional] 
**Expected** | Pointer to **NullableString** |  | [optional] 
**Actual** | Pointer to **NullableString** |  | [optional] 
**PendingUncheckpointed** | Pointer to **NullableInt32** |  | [optional] 
**LastCheckpointTx** | Pointer to **NullableInt32** |  | [optional] 
**ActiveConnections** | Pointer to **NullableInt32** |  | [optional] 
**MaxConnections** | Pointer to **NullableInt32** |  | [optional] 
**Utilization** | Pointer to **NullableString** |  | [optional] 
**UsefulFactsRatio** | Pointer to **NullableFloat32** |  | [optional] 
**DuplicatesRatio** | Pointer to **NullableFloat32** |  | [optional] 
**TotalFacts** | Pointer to **NullableInt32** |  | [optional] 

## Methods

### NewHealthCheckDetail

`func NewHealthCheckDetail(status string, ) *HealthCheckDetail`

NewHealthCheckDetail instantiates a new HealthCheckDetail object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewHealthCheckDetailWithDefaults

`func NewHealthCheckDetailWithDefaults() *HealthCheckDetail`

NewHealthCheckDetailWithDefaults instantiates a new HealthCheckDetail object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetStatus

`func (o *HealthCheckDetail) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *HealthCheckDetail) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *HealthCheckDetail) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetDetail

`func (o *HealthCheckDetail) GetDetail() string`

GetDetail returns the Detail field if non-nil, zero value otherwise.

### GetDetailOk

`func (o *HealthCheckDetail) GetDetailOk() (*string, bool)`

GetDetailOk returns a tuple with the Detail field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDetail

`func (o *HealthCheckDetail) SetDetail(v string)`

SetDetail sets Detail field to given value.

### HasDetail

`func (o *HealthCheckDetail) HasDetail() bool`

HasDetail returns a boolean if a field has been set.

### SetDetailNil

`func (o *HealthCheckDetail) SetDetailNil(b bool)`

 SetDetailNil sets the value for Detail to be an explicit nil

### UnsetDetail
`func (o *HealthCheckDetail) UnsetDetail()`

UnsetDetail ensures that no value is present for Detail, not even an explicit nil
### GetVersion

`func (o *HealthCheckDetail) GetVersion() string`

GetVersion returns the Version field if non-nil, zero value otherwise.

### GetVersionOk

`func (o *HealthCheckDetail) GetVersionOk() (*string, bool)`

GetVersionOk returns a tuple with the Version field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVersion

`func (o *HealthCheckDetail) SetVersion(v string)`

SetVersion sets Version field to given value.

### HasVersion

`func (o *HealthCheckDetail) HasVersion() bool`

HasVersion returns a boolean if a field has been set.

### SetVersionNil

`func (o *HealthCheckDetail) SetVersionNil(b bool)`

 SetVersionNil sets the value for Version to be an explicit nil

### UnsetVersion
`func (o *HealthCheckDetail) UnsetVersion()`

UnsetVersion ensures that no value is present for Version, not even an explicit nil
### GetExpected

`func (o *HealthCheckDetail) GetExpected() string`

GetExpected returns the Expected field if non-nil, zero value otherwise.

### GetExpectedOk

`func (o *HealthCheckDetail) GetExpectedOk() (*string, bool)`

GetExpectedOk returns a tuple with the Expected field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExpected

`func (o *HealthCheckDetail) SetExpected(v string)`

SetExpected sets Expected field to given value.

### HasExpected

`func (o *HealthCheckDetail) HasExpected() bool`

HasExpected returns a boolean if a field has been set.

### SetExpectedNil

`func (o *HealthCheckDetail) SetExpectedNil(b bool)`

 SetExpectedNil sets the value for Expected to be an explicit nil

### UnsetExpected
`func (o *HealthCheckDetail) UnsetExpected()`

UnsetExpected ensures that no value is present for Expected, not even an explicit nil
### GetActual

`func (o *HealthCheckDetail) GetActual() string`

GetActual returns the Actual field if non-nil, zero value otherwise.

### GetActualOk

`func (o *HealthCheckDetail) GetActualOk() (*string, bool)`

GetActualOk returns a tuple with the Actual field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActual

`func (o *HealthCheckDetail) SetActual(v string)`

SetActual sets Actual field to given value.

### HasActual

`func (o *HealthCheckDetail) HasActual() bool`

HasActual returns a boolean if a field has been set.

### SetActualNil

`func (o *HealthCheckDetail) SetActualNil(b bool)`

 SetActualNil sets the value for Actual to be an explicit nil

### UnsetActual
`func (o *HealthCheckDetail) UnsetActual()`

UnsetActual ensures that no value is present for Actual, not even an explicit nil
### GetPendingUncheckpointed

`func (o *HealthCheckDetail) GetPendingUncheckpointed() int32`

GetPendingUncheckpointed returns the PendingUncheckpointed field if non-nil, zero value otherwise.

### GetPendingUncheckpointedOk

`func (o *HealthCheckDetail) GetPendingUncheckpointedOk() (*int32, bool)`

GetPendingUncheckpointedOk returns a tuple with the PendingUncheckpointed field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPendingUncheckpointed

`func (o *HealthCheckDetail) SetPendingUncheckpointed(v int32)`

SetPendingUncheckpointed sets PendingUncheckpointed field to given value.

### HasPendingUncheckpointed

`func (o *HealthCheckDetail) HasPendingUncheckpointed() bool`

HasPendingUncheckpointed returns a boolean if a field has been set.

### SetPendingUncheckpointedNil

`func (o *HealthCheckDetail) SetPendingUncheckpointedNil(b bool)`

 SetPendingUncheckpointedNil sets the value for PendingUncheckpointed to be an explicit nil

### UnsetPendingUncheckpointed
`func (o *HealthCheckDetail) UnsetPendingUncheckpointed()`

UnsetPendingUncheckpointed ensures that no value is present for PendingUncheckpointed, not even an explicit nil
### GetLastCheckpointTx

`func (o *HealthCheckDetail) GetLastCheckpointTx() int32`

GetLastCheckpointTx returns the LastCheckpointTx field if non-nil, zero value otherwise.

### GetLastCheckpointTxOk

`func (o *HealthCheckDetail) GetLastCheckpointTxOk() (*int32, bool)`

GetLastCheckpointTxOk returns a tuple with the LastCheckpointTx field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastCheckpointTx

`func (o *HealthCheckDetail) SetLastCheckpointTx(v int32)`

SetLastCheckpointTx sets LastCheckpointTx field to given value.

### HasLastCheckpointTx

`func (o *HealthCheckDetail) HasLastCheckpointTx() bool`

HasLastCheckpointTx returns a boolean if a field has been set.

### SetLastCheckpointTxNil

`func (o *HealthCheckDetail) SetLastCheckpointTxNil(b bool)`

 SetLastCheckpointTxNil sets the value for LastCheckpointTx to be an explicit nil

### UnsetLastCheckpointTx
`func (o *HealthCheckDetail) UnsetLastCheckpointTx()`

UnsetLastCheckpointTx ensures that no value is present for LastCheckpointTx, not even an explicit nil
### GetActiveConnections

`func (o *HealthCheckDetail) GetActiveConnections() int32`

GetActiveConnections returns the ActiveConnections field if non-nil, zero value otherwise.

### GetActiveConnectionsOk

`func (o *HealthCheckDetail) GetActiveConnectionsOk() (*int32, bool)`

GetActiveConnectionsOk returns a tuple with the ActiveConnections field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActiveConnections

`func (o *HealthCheckDetail) SetActiveConnections(v int32)`

SetActiveConnections sets ActiveConnections field to given value.

### HasActiveConnections

`func (o *HealthCheckDetail) HasActiveConnections() bool`

HasActiveConnections returns a boolean if a field has been set.

### SetActiveConnectionsNil

`func (o *HealthCheckDetail) SetActiveConnectionsNil(b bool)`

 SetActiveConnectionsNil sets the value for ActiveConnections to be an explicit nil

### UnsetActiveConnections
`func (o *HealthCheckDetail) UnsetActiveConnections()`

UnsetActiveConnections ensures that no value is present for ActiveConnections, not even an explicit nil
### GetMaxConnections

`func (o *HealthCheckDetail) GetMaxConnections() int32`

GetMaxConnections returns the MaxConnections field if non-nil, zero value otherwise.

### GetMaxConnectionsOk

`func (o *HealthCheckDetail) GetMaxConnectionsOk() (*int32, bool)`

GetMaxConnectionsOk returns a tuple with the MaxConnections field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMaxConnections

`func (o *HealthCheckDetail) SetMaxConnections(v int32)`

SetMaxConnections sets MaxConnections field to given value.

### HasMaxConnections

`func (o *HealthCheckDetail) HasMaxConnections() bool`

HasMaxConnections returns a boolean if a field has been set.

### SetMaxConnectionsNil

`func (o *HealthCheckDetail) SetMaxConnectionsNil(b bool)`

 SetMaxConnectionsNil sets the value for MaxConnections to be an explicit nil

### UnsetMaxConnections
`func (o *HealthCheckDetail) UnsetMaxConnections()`

UnsetMaxConnections ensures that no value is present for MaxConnections, not even an explicit nil
### GetUtilization

`func (o *HealthCheckDetail) GetUtilization() string`

GetUtilization returns the Utilization field if non-nil, zero value otherwise.

### GetUtilizationOk

`func (o *HealthCheckDetail) GetUtilizationOk() (*string, bool)`

GetUtilizationOk returns a tuple with the Utilization field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUtilization

`func (o *HealthCheckDetail) SetUtilization(v string)`

SetUtilization sets Utilization field to given value.

### HasUtilization

`func (o *HealthCheckDetail) HasUtilization() bool`

HasUtilization returns a boolean if a field has been set.

### SetUtilizationNil

`func (o *HealthCheckDetail) SetUtilizationNil(b bool)`

 SetUtilizationNil sets the value for Utilization to be an explicit nil

### UnsetUtilization
`func (o *HealthCheckDetail) UnsetUtilization()`

UnsetUtilization ensures that no value is present for Utilization, not even an explicit nil
### GetUsefulFactsRatio

`func (o *HealthCheckDetail) GetUsefulFactsRatio() float32`

GetUsefulFactsRatio returns the UsefulFactsRatio field if non-nil, zero value otherwise.

### GetUsefulFactsRatioOk

`func (o *HealthCheckDetail) GetUsefulFactsRatioOk() (*float32, bool)`

GetUsefulFactsRatioOk returns a tuple with the UsefulFactsRatio field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUsefulFactsRatio

`func (o *HealthCheckDetail) SetUsefulFactsRatio(v float32)`

SetUsefulFactsRatio sets UsefulFactsRatio field to given value.

### HasUsefulFactsRatio

`func (o *HealthCheckDetail) HasUsefulFactsRatio() bool`

HasUsefulFactsRatio returns a boolean if a field has been set.

### SetUsefulFactsRatioNil

`func (o *HealthCheckDetail) SetUsefulFactsRatioNil(b bool)`

 SetUsefulFactsRatioNil sets the value for UsefulFactsRatio to be an explicit nil

### UnsetUsefulFactsRatio
`func (o *HealthCheckDetail) UnsetUsefulFactsRatio()`

UnsetUsefulFactsRatio ensures that no value is present for UsefulFactsRatio, not even an explicit nil
### GetDuplicatesRatio

`func (o *HealthCheckDetail) GetDuplicatesRatio() float32`

GetDuplicatesRatio returns the DuplicatesRatio field if non-nil, zero value otherwise.

### GetDuplicatesRatioOk

`func (o *HealthCheckDetail) GetDuplicatesRatioOk() (*float32, bool)`

GetDuplicatesRatioOk returns a tuple with the DuplicatesRatio field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDuplicatesRatio

`func (o *HealthCheckDetail) SetDuplicatesRatio(v float32)`

SetDuplicatesRatio sets DuplicatesRatio field to given value.

### HasDuplicatesRatio

`func (o *HealthCheckDetail) HasDuplicatesRatio() bool`

HasDuplicatesRatio returns a boolean if a field has been set.

### SetDuplicatesRatioNil

`func (o *HealthCheckDetail) SetDuplicatesRatioNil(b bool)`

 SetDuplicatesRatioNil sets the value for DuplicatesRatio to be an explicit nil

### UnsetDuplicatesRatio
`func (o *HealthCheckDetail) UnsetDuplicatesRatio()`

UnsetDuplicatesRatio ensures that no value is present for DuplicatesRatio, not even an explicit nil
### GetTotalFacts

`func (o *HealthCheckDetail) GetTotalFacts() int32`

GetTotalFacts returns the TotalFacts field if non-nil, zero value otherwise.

### GetTotalFactsOk

`func (o *HealthCheckDetail) GetTotalFactsOk() (*int32, bool)`

GetTotalFactsOk returns a tuple with the TotalFacts field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalFacts

`func (o *HealthCheckDetail) SetTotalFacts(v int32)`

SetTotalFacts sets TotalFacts field to given value.

### HasTotalFacts

`func (o *HealthCheckDetail) HasTotalFacts() bool`

HasTotalFacts returns a boolean if a field has been set.

### SetTotalFactsNil

`func (o *HealthCheckDetail) SetTotalFactsNil(b bool)`

 SetTotalFactsNil sets the value for TotalFacts to be an explicit nil

### UnsetTotalFacts
`func (o *HealthCheckDetail) UnsetTotalFacts()`

UnsetTotalFacts ensures that no value is present for TotalFacts, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


