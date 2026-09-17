use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use aes_gcm::{aead::{Aead, AeadCore, KeyInit, OsRng}, Aes256Gcm, Nonce, Key};
use argon2::{password_hash::{rand_core::OsRng as ArgonRng, PasswordHasher, SaltString}, Argon2};
use std::fs;

fn derive_key(password: &str, salt: &str) -> Result<Key<Aes256Gcm>, String> {
    let argon2 = Argon2::default();
    let salt_string = SaltString::from_b64(salt)
        .map_err(|e| format!("Invalid salt: {}", e))?;
    let mut hash_bytes = vec![0u8; 32];
    argon2.hash_password_into(password.as_bytes(), &salt_string, &mut hash_bytes)
        .map_err(|e| format!("Argon2 hash failed: {}", e))?;
    
    let mut key_bytes = [0u8; 32];
    key_bytes.copy_from_slice(&hash_bytes[..32]);
    Ok(*Key::<Aes256Gcm>::from_slice(&key_bytes))
}

#[pyfunction]
fn encrypt_file(file_path: &str, password: &str, salt: &str) -> PyResult<bool> {
    let data = fs::read(file_path).map_err(|e| PyValueError::new_err(e.to_string()))?;
    
    let key = derive_key(password, salt)
        .map_err(|e| PyValueError::new_err(e))?;
    
    let cipher = Aes256Gcm::new(&key);
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
    
    let mut encrypted_data = cipher.encrypt(&nonce, data.as_ref())
        .map_err(|_| PyValueError::new_err("Encryption failed!"))?;
        
    let mut final_data = nonce.to_vec();
    final_data.append(&mut encrypted_data);
    
    fs::write(file_path, final_data).map_err(|e| PyValueError::new_err(e.to_string()))?;
    
    Ok(true)
}

#[pyfunction]
fn decrypt_file(file_path: &str, password: &str, salt: &str) -> PyResult<bool> {
    let encrypted_data = fs::read(file_path).map_err(|e| PyValueError::new_err(e.to_string()))?;
    
    if encrypted_data.len() < 12 {
        return Err(PyValueError::new_err("File is corrupted or not encrypted."));
    }

    let key = derive_key(password, salt)
        .map_err(|e| PyValueError::new_err(e))?;
    
    let cipher = Aes256Gcm::new(&key);
    
    let (nonce_bytes, ciphertext) = encrypted_data.split_at(12);
    let nonce = Nonce::from_slice(nonce_bytes);
    
    let decrypted_data = cipher.decrypt(nonce, ciphertext)
        .map_err(|_| PyValueError::new_err("Decryption failed! Wrong password or corrupted data"))?;
        
    fs::write(file_path, decrypted_data).map_err(|e| PyValueError::new_err(e.to_string()))?;
    
    Ok(true)
}

#[pymodule]
fn apex_crypto(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(encrypt_file, m)?)?;
    m.add_function(wrap_pyfunction!(decrypt_file, m)?)?;
    Ok(())
}