package com.example.orderdesk.common;

/** The only error body this service returns: {"code": "...", "message": "..."}. */
public record ApiError(String code, String message) {}
