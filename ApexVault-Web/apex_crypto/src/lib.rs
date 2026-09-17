use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use aes_gcm::{aead::{Aead, AeadCore, KeyInit, OsRng}, Aes256Gcm, Nonce, Key};
use argon2::{password_hash::{PasswordHasher, PasswordVerifier, SaltString}, Argon2};
use rand::RngCore;
use std::fs;

fn derive_key(password: &str, salt: &str) -> Result<Key<Aes256Gcm>, PyErr> {
    let argon2 = Argon2::default();
    let salt_string = SaltString::from_b64(salt)
        .map_err(|_| PyValueError::new_err("فرمت نمک (Salt) معتبر نیست! باید Base64 باشد."))?;

    let password_hash = argon2.hash_password(password.as_bytes(), &salt_string)
        .map_err(|e| PyValueError::new_err(format!("خطای Argon2: {}", e)))?;

    let hash_bytes = password_hash.hash
        .ok_or_else(|| PyValueError::new_err("تولید خروجی هش با خطا مواجه شد."))?;

    let bytes = hash_bytes.as_bytes();
    if bytes.len() < 32 {
        return Err(PyValueError::new_err("طول کلید هش شده برای AES-256 کافی نیست."));
    }

    let mut key_bytes = [0u8; 32];
    key_bytes.copy_from_slice(&bytes[..32]);
    Ok(*Key::<Aes256Gcm>::from_slice(&key_bytes))
}

#[pyfunction]
fn encrypt_file(file_path: &str, password: &str, salt: &str) -> PyResult<bool> {
    let data = fs::read(file_path).map_err(|e| PyValueError::new_err(e.to_string()))?;

    let key = derive_key(password, salt)?;
    let cipher = Aes256Gcm::new(&key);
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng);

    let mut encrypted_data = cipher.encrypt(&nonce, data.as_ref())
        .map_err(|_| PyValueError::new_err("رمزنگاری با خطا مواجه شد!"))?;

    let mut final_data = nonce.to_vec();
    final_data.append(&mut encrypted_data);

    fs::write(file_path, final_data).map_err(|e| PyValueError::new_err(e.to_string()))?;

    Ok(true)
}

#[pyfunction]
fn decrypt_file(file_path: &str, password: &str, salt: &str) -> PyResult<bool> {
    let encrypted_data = fs::read(file_path).map_err(|e| PyValueError::new_err(e.to_string()))?;

    if encrypted_data.len() < 12 {
        return Err(PyValueError::new_err("فایل آسیب دیده است یا فرمت رمزنگاری معتبری ندارد."));
    }

    let key = derive_key(password, salt)?;
    let cipher = Aes256Gcm::new(&key);

    let (nonce_bytes, ciphertext) = encrypted_data.split_at(12);
    let nonce = Nonce::from_slice(nonce_bytes);

    let decrypted_data = cipher.decrypt(nonce, ciphertext)
        .map_err(|_| PyValueError::new_err("رمزگشایی ناموفق بود! احتمالاً رمز عبور اشتباه است."))?;

    fs::write(file_path, decrypted_data).map_err(|e| PyValueError::new_err(e.to_string()))?;

    Ok(true)
}

const NONCE_LEN: usize = 12;
const TAG_LEN: usize = 16;

fn key_from_bytes(data: &[u8], salt_b64: &str) -> Result<Key<Aes256Gcm>, PyErr> {
    let argon2 = Argon2::default();
    let salt_string = SaltString::from_b64(salt_b64)
        .map_err(|_| PyValueError::new_err("bad salt encoding"))?;
    let password_hash = argon2.hash_password(data, &salt_string)
        .map_err(|e| PyValueError::new_err(format!("Argon2 error: {}", e)))?;
    let bytes = password_hash.hash.ok_or_else(|| {
        PyValueError::new_err("hash derivation failed")
    })?.as_bytes().to_vec();
    if bytes.len() < 32 {
        return Err(PyValueError::new_err("derived key too short"));
    }
    Ok(*Key::<Aes256Gcm>::from_slice(&bytes[..32]))
}

#[pyfunction]
fn gcm_encrypt(key: &[u8], plaintext: &[u8]) -> PyResult<Vec<u8>> {
    if key.len() != 32 {
        return Err(PyValueError::new_err("key must be exactly 32 bytes"));
    }
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key));
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
    let ct = cipher.encrypt(&nonce, plaintext)
        .map_err(|_| PyValueError::new_err("encryption failed"))?;
    let mut out = nonce.to_vec();
    out.extend_from_slice(&ct);
    Ok(out)
}

#[pyfunction]
fn gcm_decrypt(key: &[u8], blob: &[u8]) -> PyResult<Vec<u8>> {
    if key.len() != 32 {
        return Err(PyValueError::new_err("key must be exactly 32 bytes"));
    }
    if blob.len() < NONCE_LEN + TAG_LEN {
        return Err(PyValueError::new_err("blob truncated"));
    }
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key));
    let (nonce_bytes, rest) = blob.split_at(NONCE_LEN);
    let nonce = Nonce::from_slice(nonce_bytes);
    cipher.decrypt(nonce, rest)
        .map_err(|_| PyValueError::new_err("decryption failed"))
}

#[pyfunction]
fn random_bytes(n: usize) -> Vec<u8> {
    let mut buf = vec![0u8; n];
    OsRng.fill_bytes(&mut buf);
    buf
}

#[pyfunction]
fn verify_password_hash(password: &str, phc_hash: &str) -> bool {
    let parsed = match argon2::password_hash::PasswordHash::new(phc_hash) {
        Ok(h) => h,
        Err(_) => return false,
    };
    Argon2::default()
        .verify_password(password.as_bytes(), &parsed)
        .is_ok()
}

#[pymodule]
fn apex_crypto(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(encrypt_file, m)?)?;
    m.add_function(wrap_pyfunction!(decrypt_file, m)?)?;
    m.add_function(wrap_pyfunction!(gcm_encrypt, m)?)?;
    m.add_function(wrap_pyfunction!(gcm_decrypt, m)?)?;
    m.add_function(wrap_pyfunction!(random_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(verify_password_hash, m)?)?;
    Ok(())
}
