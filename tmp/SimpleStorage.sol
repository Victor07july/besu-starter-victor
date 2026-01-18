// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract SimpleStorage {
    uint256 public favoriteInt;

    function store(uint256 _favoriteNumber) public {
        favoriteInt = _favoriteNumber;
    }
}