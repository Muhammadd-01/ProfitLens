import { useState, useRef, type DragEvent, type ChangeEvent } from 'react';
import { UploadCloud, FileSpreadsheet, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import api from '@/lib/api';
import type { AxiosProgressEvent } from 'axios';
import type { DatasetUploadResponse } from '@/types';

interface FileDropzoneProps {
  onUploadSuccess: (dataset: DatasetUploadResponse) => void;
}

export function FileDropzone({ onUploadSuccess }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [uploadedResult, setUploadedResult] = useState<DatasetUploadResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndUpload = async (file: File) => {
    setError(null);

    // Validate format
    const validExtensions = ['.csv', '.xlsx'];
    const fileNameLower = file.name.toLowerCase();
    const isValidExtension = validExtensions.some((ext) => fileNameLower.endsWith(ext));

    if (!isValidExtension) {
      setError('Please upload a valid CSV or XLSX spreadsheet file.');
      return;
    }

    // Validate size (50MB limit)
    const maxSizeBytes = 50 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      setError('File size exceeds the 50MB limit. Please provide a smaller dataset.');
      return;
    }

    if (file.size === 0) {
      setError('The selected file is empty. Please select a valid dataset.');
      return;
    }

    // Upload with progress tracking
    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post<DatasetUploadResponse>('/datasets/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent: AxiosProgressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percent);
          }
        },
      });

      setUploadedResult(response.data);
      onUploadSuccess(response.data);
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(message || 'Failed to process and upload dataset. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      validateAndUpload(file);
    }
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      validateAndUpload(file);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (uploadedResult) {
    return (
      <Card className="border-border bg-card">
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-emerald-500/10 p-2 text-emerald-400">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-semibold text-lg text-foreground">Dataset Detected</h3>
              <p className="text-sm text-muted-foreground">{uploadedResult.name}</p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 pt-2">
            <div className="rounded-lg bg-secondary/40 p-3 text-center">
              <span className="text-xs text-muted-foreground uppercase font-medium">Rows</span>
              <p className="text-xl font-bold text-foreground mt-0.5">
                {uploadedResult.row_count.toLocaleString()}
              </p>
            </div>
            <div className="rounded-lg bg-secondary/40 p-3 text-center">
              <span className="text-xs text-muted-foreground uppercase font-medium">Columns</span>
              <p className="text-xl font-bold text-foreground mt-0.5">
                {uploadedResult.column_count}
              </p>
            </div>
            <div className="rounded-lg bg-secondary/40 p-3 text-center">
              <span className="text-xs text-muted-foreground uppercase font-medium">Size</span>
              <p className="text-xl font-bold text-foreground mt-0.5">
                {formatFileSize(uploadedResult.file_size_bytes)}
              </p>
            </div>
          </div>

          {/* Detected columns chips */}
          <div className="space-y-1.5 pt-2">
            <span className="text-xs text-muted-foreground font-medium">Detected Columns:</span>
            <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
              {uploadedResult.columns.map((col: string) => (
                <Badge key={col} variant="secondary" className="text-xs font-normal">
                  {col}
                </Badge>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setUploadedResult(null);
                setUploadProgress(0);
              }}
            >
              Upload Another
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-all duration-200',
          isDragging
            ? 'border-primary bg-primary/5 scale-[1.01]'
            : 'border-border bg-card/50 hover:border-primary/50 hover:bg-card'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx"
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="rounded-full bg-secondary p-4 mb-4 text-muted-foreground group-hover:text-foreground">
          {isUploading ? (
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          ) : (
            <UploadCloud className="h-8 w-8 text-primary" />
          )}
        </div>

        <h3 className="text-lg font-semibold text-foreground mb-1">
          Drop your business data here
        </h3>
        <p className="text-sm text-muted-foreground mb-4 max-w-sm">
          Drag and drop your spreadsheet or click to browse files from your computer
        </p>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs text-muted-foreground">
            <FileSpreadsheet className="h-3.5 w-3.5 mr-1" /> CSV or XLSX
          </Badge>
          <span className="text-xs text-muted-foreground">• Max 50 MB</span>
        </div>

        {isUploading && (
          <div className="w-full max-w-xs mt-6 space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Uploading dataset...</span>
              <span>{uploadProgress}%</span>
            </div>
            <Progress value={uploadProgress} className="h-2" />
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive border border-destructive/20">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
