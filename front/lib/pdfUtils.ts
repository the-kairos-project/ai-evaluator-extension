/**
 * Utilities for handling PDF files in the frontend
 */

import { Logger } from './logger';

/**
 * Downloads a file from a URL and returns it as a base64-encoded string
 * 
 * @param url URL of the file to download
 * @returns Promise resolving to base64-encoded string of the file
 */
export async function downloadAndEncodeFile(url: string): Promise<string> {
  try {
    Logger.debug(`🔄 Downloading file from URL: ${url}`);
    
    // Fetch the file
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to download file: ${response.status} ${response.statusText}`);
    }
    
    // Get file as blob
    const blob = await response.blob();
    Logger.info(`✅ File downloaded successfully: ${blob.size} bytes, type: ${blob.type}`);
    
    // Convert blob to base64
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        // reader.result contains the base64 data URL
        const base64String = reader.result as string;
        // Extract the base64 part (remove the data URL prefix)
        const base64Data = base64String.split(',')[1];
        Logger.info(`✅ File encoded to base64: ${base64Data.length} characters`);
        resolve(base64Data);
      };
      reader.onerror = () => {
        reject(new Error('Failed to read file as base64'));
      };
      reader.readAsDataURL(blob);
    });
  } catch (error) {
    Logger.error(`❌ Error downloading/encoding file: ${error.message}`);
    throw error;
  }
}

/**
 * Validates if a URL points to a PDF file
 * 
 * @param url URL to validate
 * @returns boolean indicating if URL likely points to a PDF
 */
export function isPdfUrl(url: string): boolean {
  // Check if URL ends with .pdf
  if (url.toLowerCase().endsWith('.pdf')) {
    return true;
  }
  
  // Check if URL contains PDF indicators
  if (url.toLowerCase().includes('pdf') || 
      url.toLowerCase().includes('resume') || 
      url.toLowerCase().includes('cv')) {
    return true;
  }
  
  return false;
}