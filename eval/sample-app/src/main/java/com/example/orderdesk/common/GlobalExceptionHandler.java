package com.example.orderdesk.common;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

  @ExceptionHandler(NotFoundException.class)
  public ResponseEntity<ApiError> notFound(NotFoundException e) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ApiError("NOT_FOUND", e.getMessage()));
  }

  @ExceptionHandler(InvalidStateException.class)
  public ResponseEntity<ApiError> invalidState(InvalidStateException e) {
    return ResponseEntity.status(HttpStatus.CONFLICT).body(new ApiError("INVALID_STATE", e.getMessage()));
  }

  @ExceptionHandler({MethodArgumentNotValidException.class, IllegalArgumentException.class})
  public ResponseEntity<ApiError> badRequest(Exception e) {
    return ResponseEntity.badRequest().body(new ApiError("VALIDATION_FAILED", "Request is not valid"));
  }

  @ExceptionHandler(AccessDeniedException.class)
  public ResponseEntity<ApiError> forbidden(AccessDeniedException e) {
    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(new ApiError("FORBIDDEN", "Not allowed"));
  }
}
